# DDJ-REV1 no rekordbox: macOS e Windows

Projeto experimental que adapta uma instalação própria do rekordbox para reconhecer a controladora Pioneer DJ **DDJ-REV1** usando um perfil baseado na DDJ-FLX4. O repositório contém instaladores, mapeamentos e código-fonte; **não inclui nem distribui o rekordbox**. Não é um projeto oficial da AlphaTheta/Pioneer DJ.

## Compatibilidade e estado dos testes

| Plataforma | Versão exata | Situação |
|---|---|---|
| macOS Intel | rekordbox **6.8.5.0002** | Alvo: MacBook Pro 2011 com Ventura 13.7.8. Alterações verificadas no executável original; **a cópia e a controladora ainda precisam ser testadas no Mac**. |
| Windows x64 | rekordbox **7.2.14**, build identificado pelo SHA-256 abaixo | Reconhecimento e jogs 1–4 testados com uma REV1. A ativação dos jogs 3/4 foi confirmada em memória; o procedimento de instalação e inicialização publicado requer teste de ponta a ponta em uma instalação limpa. |

O instalador recusa executáveis com hash diferente, mesmo que a versão exibida seja a mesma. O **mesmo CSV de mapeamento dos quatro decks** usado no Windows já está incluído no Mac. **A correção dos processadores de jog 3/4, os efeitos especiais e o mixer de fone do Windows ainda não foram portados para o Mac.** As entradas do CSV, por si só, não comprovam que os jogs 3/4 funcionem nele.

## macOS — prioridade para o MacBook Pro 2011

### Requisitos

1. Mac Intel com macOS Ventura 13.7.8 e rekordbox **6.8.5.0002** instalado em `/Applications/rekordbox 6/rekordbox.app`. Instale o software original por uma fonte oficial da AlphaTheta/Pioneer DJ.
2. Python 3 disponível no Terminal (`python3 --version`).
3. A pasta completa deste repositório. Em GitHub, escolha **Code → Download ZIP**, descompacte o arquivo e abra o Terminal na pasta `macos` dentro dele. Por exemplo, se foi extraído em Downloads:

   ```bash
   cd ~/Downloads/rekordbox_for_everyone-main/macos
   ```

### Instalar e testar

Feche o rekordbox antes de começar. No Terminal, execute:

```bash
python3 install.py --check
python3 install.py
```

O primeiro comando apenas verifica a compatibilidade; execute o segundo somente se a verificação passar. Se o aplicativo original estiver em outro caminho, informe-o em ambos os comandos, por exemplo:

```bash
python3 install.py --app "/Applications/Outro local/rekordbox.app" --check
python3 install.py --app "/Applications/Outro local/rekordbox.app"
```

O instalador cria **`~/Applications/rekordbox REV1 6.8.5.app`**, preservando o aplicativo original, e não substitui uma cópia já existente. Se houver um mapeamento pessoal REV1 em um dos caminhos conhecidos, salva um backup antes de substituí-lo. Ele assina a cópia localmente; a verificação da assinatura não garante que o programa abrirá em todos os Macs.

Conecte a REV1 e abra a **cópia**, por exemplo:

```bash
open "$HOME/Applications/rekordbox REV1 6.8.5.app"
```

Confira reconhecimento, áudio, PLAY, CUE, pads, LEDs, jogs e FX. Para um diagnóstico somente de leitura, execute `python3 diagnostico.py` na pasta `macos`. Ele informa versão, modelo, compatibilidade do executável e assinatura local; o resultado não contém o número de série USB. Se a verificação ou abertura falhar, compartilhe a mensagem de erro e a saída do diagnóstico para investigação.

### Cópia experimental com pads de stems

Na pasta clonada, atualize os arquivos com `git pull`. Feche o rekordbox e, na pasta `macos`, execute:

```bash
python3 install.py --stems --check
python3 install.py --stems
open "$HOME/Applications/rekordbox REV1 Stems 6.8.5.app"
```

Isso cria uma segunda cópia, sem substituir a cópia REV1 existente. No modo **Sampler**, os pads 1, 2 e 3 são mapeados para **DRUMS**, **VOCAL** e **INST**; os outros pads do modo Sampler e suas funções com SHIFT são removidos desse perfil. Os outros modos do mapeamento são preservados. O rekordbox 6.8.5 contém os identificadores dessas três funções, mas **o acionamento, os LEDs e a sincronização com os botões da tela ainda não foram verificados na REV1 com macOS**. Teste com uma faixa carregada e relate o resultado; se os LEDs ou as funções não responderem, não os considere validados.

O mapeamento pessoal REV1 é compartilhado entre as cópias do rekordbox. Se ele já existir, o instalador cria um backup `DDJ-REV1.midi.csv.before-rev1-*.backup` e instala o perfil de stems nesse local, portanto a cópia REV1 anterior também poderá usar o novo perfil. Para desfazer essa troca, feche o rekordbox e restaure o backup como `DDJ-REV1.midi.csv` na mesma pasta. O aplicativo REV1 Stems pode ser removido separadamente.

### Diagnóstico dos jogs no Mac

Se a cópia abrir e a REV1 for reconhecida, o diagnóstico abaixo ajuda a adaptar os jogs 3/4 para o motor específico do macOS. Ele observa temporariamente quais decks recebem eventos de giro e toque e se existe um processador associado; **não ativa a correção**. Com a cópia aberta e a REV1 conectada, no Terminal dentro da pasta `macos` execute:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install frida==17.25.2
.venv/bin/python diagnostico_jogs.py
```

Durante os 45 segundos seguintes, selecione cada deck e toque e gire seu jog. Envie a saída exibida, inclusive qualquer erro. O programa usa instrumentação temporária no processo e não grava ou modifica o mapeamento; a conexão pode ser recusada pelas permissões ou pela assinatura do macOS. Seu resultado é necessário para verificar se a ausência dos processadores observada no Windows também ocorre no Mac.

Se estiver usando a cópia REV1 Stems, acrescente `--stems` ao último comando: `.venv/bin/python diagnostico_jogs.py --stems`.

### Remover no macOS

Feche o rekordbox e remova `~/Applications/rekordbox REV1 6.8.5.app`. Caso um mapeamento pessoal anterior tenha sido substituído, restaure o arquivo `DDJ-REV1.midi.csv.before-rev1-*.backup` para `DDJ-REV1.midi.csv` na mesma pasta. O aplicativo original continua disponível.

## Windows — rekordbox 7.2.14 x64

### Instalar

1. Instale o rekordbox 7.2.14 original no caminho padrão `C:\Program Files\rekordbox\rekordbox 7.2.14` e o Python 3 de 64 bits. Baixe e extraia o repositório completo.
2. Feche o rekordbox. Abra o **Prompt de Comando como administrador** e entre na pasta `windows` do repositório extraído, por exemplo `cd /d "C:\caminho\rekordbox_for_everyone-main\windows"`.
3. Execute:

   ```bat
   py -3 -m pip install -r requirements.txt
   py -3 install.py --check
   py -3 install.py
   ```

O instalador exige o executável original exato, salva `rekordbox.exe.bak_REV1`, altera o executável e instala o CSV. Se houver um CSV de sistema diferente ou um backup inesperado, ele interrompe para preservar os arquivos existentes. A modificação invalida a assinatura original do executável. Ela troca as referências à FLX4 pela REV1 nessa instalação, afetando o uso de uma FLX4 real.

### Usar

1. Com a REV1 conectada e o rekordbox fechado, execute **`windows\iniciar.cmd`** e mantenha a janela aberta. Não abra pelo ícone normal: o launcher aplica a correção USB e o perfil FX/CUE em memória.
2. Quando o rekordbox estiver aberto e a REV1 reconhecida, execute **`windows\ativar-jogs-3-4.cmd`**. Aguarde a confirmação e mantenha também essa janela aberta até fechar o rekordbox. Essa etapa aplica a mesma intervenção temporária confirmada no teste físico, mas o fluxo publicado ainda não foi testado integralmente.
3. Ao reconectar a controladora, feche o rekordbox e ambas as janelas e repita os passos. As alterações em memória não sobrevivem ao encerramento.

O perfil FX/CUE permite selecionar um efeito com um toque ou vários com botões simultâneos; a alavanca aplica os efeitos selecionados. SHIFT + FX 2/3 ajusta o beat dos três slots do lado correspondente. A lógica de mixer de fone foi observada em memória, mas a escuta final e todas as combinações de efeitos ainda requerem confirmação física. Mapeamentos pessoais são preservados em backup antes das entradas adicionais necessárias serem acrescentadas.

### Restaurar no Windows

Feche o rekordbox e os launchers. Restaure o backup `rekordbox.exe.bak_REV1` como `rekordbox.exe` na pasta de instalação (é necessária permissão de administrador). Se desejar, restaure também o backup pessoal `DDJ-REV1.before-fx-cue-*.backup` para `DDJ-REV1.midi.csv` em `%APPDATA%\Pioneer\rekordbox6\MidiMappings`. A reinstalação oficial do rekordbox é outra forma de restaurar o aplicativo.

## Como funciona

No macOS, o instalador copia o app, altera o nome e os identificadores USB em locais verificados do binário Intel, instala o mapeamento e assina a cópia localmente. No Windows, o instalador substitui o nome do controlador no executável verificado; o launcher usa Frida para corrigir a consulta USB em memória e aplicar o comportamento de FX/CUE. O auxiliar de jogs identifica o mapa ativo, valida seus objetos e associa temporariamente processadores nativos aos decks 3 e 4. Os endereços e layouts são específicos dos builds analisados.

SHA-256 do executável original aceito:

* macOS 6.8.5.0002: `ba9a80ea5fdb01f1981d8b05cc6b35c9b9bd480919aab58184ea3c89b90f50c5`
* Windows 7.2.14: `f6359b6b3553e5f81e55444b28b7b56aa6f80f7bb7eb88f3c84d865d821ad5a9`

## Testes de desenvolvimento

Na pasta `macos`, execute `python3 -m unittest -v test_install.py`. Na pasta `windows`, com Frida instalado, execute `py -3 -m unittest -v test_rev1_fx_cue_launcher.py`; com Node.js, execute `node test_rev1_fx_cue_state.js`, `node test_rev1_headphone_hook.js` e `node test_jog34_live_trial.js jog34_live_trial.js`. Esses testes não substituem os testes com o aplicativo e o hardware reais.
