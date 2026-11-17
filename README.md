<div align="center">

# 🛠️ Fictor IT Tools

**Suite completa (ou quase) de ferramentas para técnicos de informática, para Windows 10/11.**
Interface em estilo *Frutiger Aero* moderno: vidro, reflexos, bolhas e tons de azul.
Em breve adicionarei mais estilos de interface diferentes, em diferentes edições.

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-2d8cff?logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-0a4fc4?logo=python&logoColor=white)
![UI](https://img.shields.io/badge/UI-pywebview%20%2B%20HTML%2FCSS-7fe0ff)

<!-- Adicione aqui uma captura de ecrã: ![Screenshot](docs/screenshot.png) -->

</div>

---

## ✨ Funcionalidades

| Aba | O que faz |
|---|---|
| 🖥️ **Sistema** | Placa-mãe, BIOS, CPU (clock, núcleos, threads, cache), RAM (GB, tipo, velocidade, voltagem, fabricante), GPU, discos e Sistema Operativo, em cartões de vidro |
| 💽 **Discos** | Saúde dos discos (S.M.A.R.T.): estado, temperatura, desgaste, horas ligado, erros e previsão de falha |
| 🔋 **Energia** | Bateria, ligação à corrente e plano de energia ativo |
| 🧩 **Drivers** | Catálogo de drivers instalados, instalação/atualização via Windows Update e atalhos para as páginas oficiais (Intel, AMD, NVIDIA, ASUS, MSI, Gigabyte, Realtek, Dell, HP, Lenovo) |
| 🚀 **Arranque** | Ativar/desativar programas do arranque automático (reversível) |
| 📦 **Apps** | Instalar, desinstalar, pesquisar e atualizar apps através do `winget`, com catálogo de ferramentas de técnico |
| 🌡️ **Sensores** | Tempo real: carga de CPU e por núcleo, clock, RAM, disco, temperaturas, voltagens, ventoinhas e **consumo em watts com gráfico dos últimos 5 minutos** |
| ⚖️ **Bottleneck** | Deteta e calcula o gargalo CPU/GPU a 1080p, 1440p ou 4K |
| 🧹 **Debloat** | Remove apps indesejadas, desativa telemetria, ID de publicidade e histórico de atividades; cria ponto de restauro |
| 🌐 **Rede** | Latência e perda de pacotes (1.1.1.1 e 8.8.8.8) e speedtest de download/upload |
| 📄 **Relatórios** | Exporta um relatório completo em **HTML**, **JSON** ou **PDF** |

---

## 📋 Requisitos

- Windows 10 ou 11 (x64)
- [Python 3.10+](https://www.python.org/downloads/) (apenas para executar a partir do código ou compilar)
- WebView2 Runtime (já incluído no Windows 10/11 atualizado)
- Recomendado: executar como **administrador** (S.M.A.R.T., debloat e arranque do sistema precisam)
- Opcional: [LibreHardwareMonitor](https://librehardwaremonitor.org) aberto em segundo plano para sensores completos

## 🚀 Como executar

Basta executar o executável `FictorITTools.exe`

## 🔨 Compilar para .EXE

```bash
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --uac-admin --add-data "ui;ui" --name RuiTechSuite techsuite.py
```
Ou duplo clique em `build.bat`. O executável fica em `dist\FictorITTools.exe` e pede permissões de administrador ao abrir.

---

## 📁 Estrutura

```
FictorITTools/
├── techsuite.py       # backend (recolha de dados, ações, ponte pywebview)
├── ui/
│   └── index.html     # interface Frutiger Aero (HTML + CSS + JS)
├── requirements.txt
├── build.bat          # compilação para .exe
└── README.md
```

---

## ⚠️ Limitações conhecidas

- **Consumo em watts:** um software não mede o que sai da tomada. A suite usa, por ordem: taxa de descarga da bateria (consumo total real do portátil), soma CPU + GPU via LibreHardwareMonitor, ou uma estimativa pela carga do CPU (assinalada como imprecisa). Para o consumo total de um desktop, só um medidor externo.
- **Sensores:** voltagens, ventoinhas e watts completos exigem o LibreHardwareMonitor aberto.
- **Bottleneck:** é uma estimativa heurística (núcleos × clock / modelo da GPU), não substitui benchmarks reais.
- **Drivers:** a instalação automática é feita pelo Windows Update; para as marcas, a suite abre as páginas oficiais.
- **VRAM da GPU:** o WMI pode reportar no máximo 4 GB em placas com mais memória.
- **Debloat:** altera o sistema. Crie um ponto de restauro antes de aplicar.
- **Speedtest:** usa servidores da Cloudflare (com alternativa da OVH para o download). Firewalls ou antivírus podem bloquear o upload.

---

## 🧰 Tecnologias

[Python](https://www.python.org/) · [pywebview](https://pywebview.flowrl.com/) · [psutil](https://github.com/giampaolo/psutil) · [ReportLab](https://www.reportlab.com/) · PowerShell/CIM · winget · HTML/CSS/JS

## 👤 Autor

**Rui Ramalho** — [@ruiramalhoofc](https://github.com/ruiramalhoofc) · [ruiramalhoofc.github.io](https://ruiramalhoofc.github.io)
