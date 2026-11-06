/* Experimental: somente rekordbox 7.2.14 Windows x64 identificado pelo launcher. */
(function () {
  'use strict';
  const base = Process.getModuleByName('rekordbox.exe').base;
  const winmm = Process.getModuleByName('winmm.dll');
  const getInCaps = new NativeFunction(winmm.getExportByName('midiInGetDevCapsW'), 'uint', ['uint64', 'pointer', 'uint']);
  const getOutCaps = new NativeFunction(winmm.getExportByName('midiOutGetDevCapsW'), 'uint', ['uint64', 'pointer', 'uint']);
  const outShort = new NativeFunction(winmm.getExportByName('midiOutShortMsg'), 'uint', ['pointer', 'uint']);
  const callback = new NativeFunction(base.add(0xfbcbd0), 'void', ['pointer', 'uint', 'pointer', 'pointer', 'pointer']);
  const machine = globalThis.createRev1FxCueState();
  const pendingInput = new Map(), pendingOutput = new Map();
  let inputHandle = null, outputHandle = null, injecting = false;
  let headphoneObject = null, mixerFinder = null, mixTimer = null;
  const headphoneVtable = base.add(0x54b5f48);

  function refreshHeadphoneMix() {
    if (!headphoneObject) { armMixerFinder(); return; }
    try {
      if (!headphoneObject.readPointer().equals(headphoneVtable)) {
        headphoneObject = null;
        armMixerFinder();
        return;
      }
      const master = headphoneObject.add(0x68).readU8() !== 0;
      const maskPointer = headphoneObject.add(0x48).readPointer();
      if (maskPointer.isNull()) return;
      const cueMask = maskPointer.readU32();
      const wanted = machine.engineMixValue(master, cueMask);
      headphoneObject.add(0x40).writeFloat(wanted);
      send('FX/CUE: mixer fone master=' + Number(master) + ' canais=' + cueMask + ' posicao=' + wanted);
    } catch (e) {
      headphoneObject = null;
      send('FX/CUE: mixer de fone indisponivel: ' + e);
      armMixerFinder();
    }
  }
  function scheduleHeadphoneMix() {
    if (mixTimer !== null) clearTimeout(mixTimer);
    mixTimer = setTimeout(function () { mixTimer = null; refreshHeadphoneMix(); }, 60);
  }
  function armMixerFinder() {
    if (mixerFinder !== null) return;
    let captured = false;
    mixerFinder = Interceptor.attach(base.add(0x2de7320), {
      onEnter(args) {
        if (captured) return;
        try {
          if (!args[0].readPointer().equals(headphoneVtable)) return;
          headphoneObject = ptr(args[0].toString());
          captured = true;
          setImmediate(function () {
            if (mixerFinder !== null) { mixerFinder.detach(); mixerFinder = null; }
            send('FX/CUE: mixer de fone identificado');
            scheduleHeadphoneMix();
          });
        } catch (_) {}
      }
    });
  }
  Interceptor.attach(base.add(0x1098890), {
    onEnter(args) {
      if (headphoneObject && args[0].equals(headphoneObject)) {
        headphoneObject = null;
        setImmediate(armMixerFinder);
      }
    }
  });
  armMixerFinder();

  function isRev1(getCaps, index, size) {
    try {
      const caps = Memory.alloc(size);
      return getCaps(index, caps, size) === 0 && caps.add(8).readUtf16String() === 'DDJ-REV1';
    } catch (e) { send('FX/CUE: erro consultando porta ' + e); return false; }
  }
  function packed(m) { return (m[0] | (m[1] << 8) | (m[2] << 16)) >>> 0; }
  function dispatch(result, handle, instance, timestamp) {
    if (!result.input.length && !result.output.length) return;
    setImmediate(function () {
      if (!inputHandle || !handle.equals(inputHandle)) return;
      try {
        injecting = true;
        for (const message of result.input) callback(handle, 0x3c3, instance, ptr(packed(message)), timestamp);
        if (outputHandle) for (const message of result.output) {
          const code = outShort(outputHandle, packed(message));
          if (code !== 0) send('FX/CUE: envio de LED falhou, codigo=' + code);
        }
      } catch (e) { send('FX/CUE: falha ao encaminhar MIDI: ' + e); }
      finally { injecting = false; }
    });
  }

  Interceptor.attach(base.add(0xfbd1be), {
    onEnter() {
      const index = this.context.rdx.toUInt32();
      if (isRev1(getInCaps, index, 76)) pendingInput.set(this.threadId, this.context.rcx);
    }
  });
  Interceptor.attach(base.add(0xfbd1c4), {
    onEnter() {
      const target = pendingInput.get(this.threadId);
      pendingInput.delete(this.threadId);
      if (target && this.context.rax.toInt32() === 0) {
        inputHandle = target.readPointer();
        send('FX/CUE: entrada REV1 identificada');
      }
    }
  });
  Interceptor.attach(base.add(0xfbdaa5), {
    onEnter() {
      const index = this.context.rdx.toUInt32();
      if (isRev1(getOutCaps, index, 84)) pendingOutput.set(this.threadId, this.context.rcx);
    }
  });
  Interceptor.attach(base.add(0xfbdaab), {
    onEnter() {
      const target = pendingOutput.get(this.threadId);
      pendingOutput.delete(this.threadId);
      if (target && this.context.rax.toInt32() === 0) {
        outputHandle = target.readPointer();
        send('FX/CUE: saida REV1 identificada');
      }
    }
  });
  Interceptor.attach(base.add(0xfbde1c), {
    onEnter() {
      if (!outputHandle || !this.context.rcx.equals(outputHandle)) return;
      const value = this.context.rdx.toUInt32();
      const status = value & 0xff, control = (value >>> 8) & 0x7f, level = (value >>> 16) & 0x7f;
      machine.observeOutput(status, control, level);
      if ((status === 0x96 && control === 0x63) ||
          ((status === 0x90 || status === 0x91) && control === 0x54)) scheduleHeadphoneMix();
      const armed = machine.armedLed(status, control);
      if (armed !== null) this.context.rdx = ptr((value & 0xff00ffff) | (armed << 16));
    }
  });
  Interceptor.attach(base.add(0xfbcbd0), {
    onEnter(args) {
      if (injecting || !inputHandle || !args[0].equals(inputHandle) || args[1].toUInt32() !== 0x3c3) return;
      const data = args[3].toUInt32();
      const result = machine.process(data & 0xff, (data >>> 8) & 0x7f, (data >>> 16) & 0x7f);
      if (!result.handled) return;
      const handle = ptr(args[0].toString()), instance = ptr(args[2].toString());
      const timestamp = ptr(args[4].toString());
      // Keep the original callback's lifetime/cleanup path but suppress this event.
      args[1] = ptr(0);
      dispatch(result, handle, instance, timestamp);
      if (result.scheduleFx) {
        const pending = result.scheduleFx;
        setTimeout(function () {
          if (inputHandle && handle.equals(inputHandle)) {
            dispatch(machine.flushFx(pending.side, pending.generation), handle, instance, timestamp);
          }
        }, 80);
      }
    }
  });
  send('FX/CUE: controles experimentais carregados');
})();
