#!/usr/bin/env python3
# Fictor IT Tools - suite para técnicos de informática (Windows 10/11)
import json, subprocess, threading, time, os, re, sys, platform, webbrowser, datetime, ctypes
import webview
import urllib.request
import psutil
try:
    import winreg
except ImportError:
    winreg = None

BG, PN, AC, FG, HI, TX = "#070d24", "#101c44", "#2f6bff", "#cfe0ff", "#6fa8ff", "#7fd0ff"
CF = ("Consolas", 10)
NOWIN = 0x08000000
REPORT = {}


def ps(cmd, js=False, timeout=90):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True,
                       timeout=timeout, creationflags=NOWIN)
    out = r.stdout.decode("utf-8", "ignore").strip()
    if js:
        try:
            d = json.loads(out)
            return d if isinstance(d, list) else [d]
        except Exception:
            return []
    return out or r.stderr.decode("utf-8", "ignore").strip()


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ---------------------------------------------------------------- recolha de dados
PS_INFO = r'''
$o=[ordered]@{
placa=Get-CimInstance Win32_BaseBoard|Select Manufacturer,Product,Version,SerialNumber
bios=Get-CimInstance Win32_BIOS|Select Manufacturer,SMBIOSBIOSVersion,ReleaseDate
cpu=Get-CimInstance Win32_Processor|Select Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed,L2CacheSize,L3CacheSize,SocketDesignation,VirtualizationFirmwareEnabled
ram=Get-CimInstance Win32_PhysicalMemory|Select Manufacturer,PartNumber,Capacity,Speed,ConfiguredClockSpeed,ConfiguredVoltage,MinVoltage,MaxVoltage,SMBIOSMemoryType,BankLabel
gpu=Get-CimInstance Win32_VideoController|Select Name,AdapterRAM,DriverVersion,VideoProcessor,VideoArchitecture,CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate
discos=Get-CimInstance Win32_DiskDrive|Select Model,Size,InterfaceType,MediaType,SerialNumber
os=Get-CimInstance Win32_OperatingSystem|Select Caption,Version,BuildNumber,OSArchitecture,InstallDate,LastBootUpTime
}
$o|ConvertTo-Json -Depth 4 -Compress
'''
MEMTYPE = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 34: "DDR5", 35: "LPDDR5"}


def get_info():
    raw = ps(PS_INFO, timeout=120)
    try:
        d = json.loads(raw)
    except Exception:
        return {}
    return {k: (v if isinstance(v, list) else [v]) for k, v in d.items()}


def fmt_val(k, v):
    if v is None or v == "":
        return "-"
    if k in ("Capacity", "Size", "AdapterRAM") and isinstance(v, (int, float)) and v > 1e6:
        gb = v / 1024 ** 3
        return f"{gb:.1f} GB" + (" (VRAM reportada pelo WMI; pode estar limitada a 4GB)" if k == "AdapterRAM" else "")
    if k in ("ConfiguredVoltage", "MinVoltage", "MaxVoltage") and isinstance(v, (int, float)):
        return f"{v / 1000:.2f} V" if v else "-"
    if k in ("MaxClockSpeed", "CurrentClockSpeed"):
        return f"{v / 1000:.2f} GHz"
    if k in ("Speed", "ConfiguredClockSpeed"):
        return f"{v} MHz"
    if k in ("L2CacheSize", "L3CacheSize"):
        return f"{v} KB"
    if k == "SMBIOSMemoryType":
        return MEMTYPE.get(v, str(v))
    return str(v)


def fmt_info(info):
    out = []
    for sec, items in info.items():
        out.append(f"\n=== {sec.upper()} ===")
        for it in items:
            for k, v in (it or {}).items():
                out.append(f"  {k:<28}{fmt_val(k, v)}")
            out.append("  " + "-" * 40)
    c = psutil.cpu_freq()
    out.append("\n=== CPU (live) ===")
    out.append(f"  Núcleos físicos/lógicos     {psutil.cpu_count(False)}/{psutil.cpu_count()}")
    if c:
        out.append(f"  Clock atual/máx             {c.current:.0f} / {c.max:.0f} MHz")
    out.append("  Potência (W)                ver aba Sensores (requer LibreHardwareMonitor)")
    vm = psutil.virtual_memory()
    out.append(f"\n=== RAM (live) ===\n  Total {vm.total / 1024 ** 3:.1f} GB | Usada {vm.percent}%")
    out.append(f"\n=== PC ===\n  {platform.node()} | {platform.platform()}")
    return "\n".join(out)


def act_info():
    info = get_info()
    REPORT["sistema"] = info
    return fmt_info(info)


def act_smart():
    d = ps(r'''Get-PhysicalDisk|%{$d=$_;$r=$d|Get-StorageReliabilityCounter;[pscustomobject]@{Nome=$d.FriendlyName;Tipo=$d.MediaType;Barramento=$d.BusType;Saude=$d.HealthStatus;Estado=$d.OperationalStatus;Tamanho=$d.Size;Temperatura=$r.Temperature;Desgaste_pct=$r.Wear;Horas_ligado=$r.PowerOnHours;Ciclos_ligar=$r.StartStopCycleCount;Erros_leitura=$r.ReadErrorsTotal;Erros_escrita=$r.WriteErrorsTotal}}|ConvertTo-Json''', True)
    pf = ps("Get-CimInstance -Namespace root/wmi MSStorageDriver_FailurePredictStatus -EA SilentlyContinue|Select InstanceName,PredictFailure|ConvertTo-Json", True)
    REPORT["discos"] = {"smart": d, "predict": pf}
    out = ["=== SAÚDE DOS DISCOS (S.M.A.R.T.) ==="]
    for x in d:
        out.append("")
        for k, v in x.items():
            out.append(f"  {k:<16}{fmt_val('Size', v) if k == 'Tamanho' else v}")
    for p in pf:
        out.append(f"\n  Previsão de falha: {'SIM!!' if p.get('PredictFailure') else 'não'}  ({p.get('InstanceName')})")
    return "\n".join(out) if d else "Sem dados (execute como administrador)."


def act_power():
    b = psutil.sensors_battery()
    out = ["=== ENERGIA ==="]
    if b:
        out.append(f"  Bateria: {b.percent:.0f}% | Ligado à corrente: {'sim' if b.power_plugged else 'não'}")
        if b.secsleft > 0:
            out.append(f"  Tempo restante: {b.secsleft // 3600}h{b.secsleft % 3600 // 60:02d}")
    else:
        out.append("  Sem bateria (desktop).")
    out.append(ps("Get-CimInstance Win32_Battery|Select Name,DesignVoltage,EstimatedChargeRemaining,BatteryStatus,Chemistry|Format-List|Out-String"))
    out.append("  Plano: " + ps("powercfg /getactivescheme"))
    out.append("  Ver relatório detalhado de bateria: powercfg /batteryreport")
    REPORT["energia"] = "\n".join(out)
    return REPORT["energia"]


def act_sensors():
    out = ["=== SENSORES ==="]
    pc = psutil.cpu_percent(percpu=True, interval=0.5)
    c = psutil.cpu_freq()
    out.append(f"CPU {sum(pc) / len(pc):.0f}% | clock {c.current:.0f} MHz" if c else f"CPU {sum(pc) / len(pc):.0f}%")
    out.append("Cores: " + " ".join(f"{p:.0f}%" for p in pc))
    out.append(f"RAM {psutil.virtual_memory().percent}%")
    lhm = ps("Get-CimInstance -Namespace root/LibreHardwareMonitor -ClassName Sensor -EA SilentlyContinue|Select Name,SensorType,Value|ConvertTo-Json -Compress", True)
    if lhm:
        by = {}
        for s in lhm:
            by.setdefault(s["SensorType"], []).append(s)
        units = {"Temperature": "°C", "Clock": "MHz", "Voltage": "V", "Fan": "RPM", "Power": "W", "Load": "%"}
        for t, lst in by.items():
            out.append(f"\n-- {t} --")
            for s in lst:
                out.append(f"  {s['Name']:<28}{s['Value']:.1f} {units.get(t, '')}")
    else:
        t = ps("Get-CimInstance -Namespace root/wmi MSAcpi_ThermalZoneTemperature -EA SilentlyContinue|%{[math]::Round($_.CurrentTemperature/10-273.15,1)}")
        out.append("\nTemp. (zona ACPI): " + (t.replace("\n", " °C, ") + " °C" if t else "indisponível"))
        out.append("Para voltagens, ventoinhas, watts e temperaturas completas: abra o\nLibreHardwareMonitor (https://librehardwaremonitor.org) em segundo plano\ne esta aba lê os sensores todos automaticamente.")
    return "\n".join(out)


def act_drivers():
    d = ps("Get-CimInstance Win32_PnPSignedDriver|?{$_.DeviceName}|Select DeviceName,Manufacturer,DriverVersion,@{n='D';e={$_.DriverDate.ToString('yyyy-MM-dd')}}|ConvertTo-Json -Compress", True, 120)
    REPORT["drivers"] = d
    return "=== CATÁLOGO DE DRIVERS ===\n" + "\n".join(
        f"{(x.get('DeviceName') or '')[:42]:<44}{(x.get('Manufacturer') or '')[:20]:<22}{x.get('DriverVersion')}  {x.get('D')}"
        for x in sorted(d, key=lambda x: x.get("DeviceName") or ""))


def act_wu():
    return ps("UsoClient StartScan; UsoClient StartDownload; UsoClient StartInstall; 'Pedido enviado ao Windows Update. Veja Definições > Windows Update.'")


VENDORS = {"Intel": "https://www.intel.com/content/www/us/en/support/detect.html", "AMD": "https://www.amd.com/en/support/download/drivers.html",
           "NVIDIA": "https://www.nvidia.com/Download/index.aspx", "ASUS": "https://www.asus.com/support/download-center/",
           "MSI": "https://www.msi.com/support/download/", "Gigabyte": "https://www.gigabyte.com/Support/Consumer/Download",
           "Realtek": "https://www.realtek.com/Download", "Dell": "https://www.dell.com/support/home/", "HP": "https://support.hp.com/drivers", "Lenovo": "https://support.lenovo.com/"}


def vendor(name):
    return lambda: (webbrowser.open(VENDORS[name]), f"Aberto: {VENDORS[name]}")[1]


# ---- bottleneck
def gpu_score(name):
    n = name.upper()
    m = re.search(r"(RTX|GTX|RX|ARC)\s*[A]?(\d{3,4})", n)
    if not m:
        return 15 if "INTEL" in n else 20
    fam, num = m.group(1), int(m.group(2))
    if fam in ("RTX", "GTX"):
        gen, tier = num // 100, num % 100
        return tier * {10: .6, 16: .7, 20: .85, 30: 1.1, 40: 1.4, 50: 1.7}.get(gen, 1)
    gen, tier = (num // 1000, (num % 1000) / 10) if num >= 1000 else (num // 100, num % 100)
    return tier * {5: .55, 6: 1.0, 7: 1.35, 9: 1.6}.get(gen, 1)


def act_bottle(res):
    def f():
        i = get_info()
        cpu, gpu = i["cpu"][0], max(i["gpu"], key=lambda g: gpu_score(g["Name"]))
        cs = cpu["MaxClockSpeed"] / 100 * (1 + .07 * min(cpu["NumberOfCores"], 12))
        gs = gpu_score(gpu["Name"]) * {1080: 1, 1440: .85, 2160: .65}[res]
        hi, lo = max(cs, gs), min(cs, gs)
        pct = (hi - lo) / hi * 100
        lim = "CPU" if cs < gs else "GPU"
        v = "equilibrado" if pct < 10 else ("ligeiro" if pct < 25 else "significativo")
        return (f"=== GARGALO @ {res}p ===\nCPU: {cpu['Name']}  (índice {cs:.0f})\nGPU: {gpu['Name']}  (índice {gs:.0f})\n\n"
                f"Limitador: {lim}\nGargalo estimado: {pct:.0f}% ({v})\n\nNOTA: estimativa heurística (núcleos x clock / modelo da GPU),\nnão substitui benchmarks reais.")
    return f


# ---- rede
def ping(host, n=20):
    o = subprocess.run(["ping", "-n", str(n), host], capture_output=True, creationflags=NOWIN).stdout.decode("cp850", "ignore")
    loss = re.search(r"\((\d+)\s*%", o)
    ms = re.findall(r"=\s*(\d+)\s*ms", o)
    return (loss.group(1) + "%" if loss else "?"), (ms[-1] + " ms" if ms else "?")


def act_net():
    out = ["=== REDE (20 pings por alvo) ==="]
    r = {}
    for h in ("1.1.1.1", "8.8.8.8"):
        l, a = ping(h)
        r[h] = {"perda": l, "latencia_media": a}
        out.append(f"  {h:<10} latência média {a:<8} perda de pacotes {l}")
    REPORT["rede"] = r
    return "\n".join(out)


def _run_test(worker, secs=8, conns=4):
    """Corre 'conns' ligações em paralelo durante 'secs' segundos; devolve (Mbps, erro)."""
    stop = time.time() + secs
    total, errs = [0], []
    lock = threading.Lock()

    def add(n):
        with lock:
            total[0] += n
    ths = [threading.Thread(target=worker, args=(stop, add, errs), daemon=True) for _ in range(conns)]
    t0 = time.time()
    for t in ths:
        t.start()
    for t in ths:
        t.join(max(0.1, stop + 6 - time.time()))
    el = max(time.time() - t0, 0.1)
    el = min(el, secs + 1)
    return (total[0] * 8 / el / 1e6 if total[0] else None), (errs[0] if errs else None)


UA = {"User-Agent": "Mozilla/5.0"}


def _dl_worker(stop, add, errs, url="https://speed.cloudflare.com/__down?bytes=25000000"):
    try:
        while time.time() < stop:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=8) as rr:
                while time.time() < stop:
                    c = rr.read(65536)
                    if not c:
                        break
                    add(len(c))
    except Exception as e:
        errs.append(str(e))


def _dl_fallback(stop, add, errs):
    _dl_worker(stop, add, errs, "https://proof.ovh.net/files/100Mb.dat")


def _ul_worker(stop, add, errs):
    data = b"0" * 500_000
    try:
        while time.time() < stop:
            urllib.request.urlopen(urllib.request.Request("https://speed.cloudflare.com/__up", data=data, method="POST", headers=UA), timeout=8).read()
            add(len(data))
    except Exception as e:
        errs.append(str(e))


def act_speed():
    d, e1 = _run_test(_dl_worker)
    src = "Cloudflare"
    if d is None:
        d, e1 = _run_test(_dl_fallback)
        src = "OVH (alternativo)"
    u, e2 = _run_test(_ul_worker)
    REPORT.setdefault("rede", {})["speedtest"] = {"download_mbps": round(d, 1) if d else None, "upload_mbps": round(u, 1) if u else None}
    out = [f"=== SPEEDTEST ({src}, 4 ligações, ~8s cada) ===",
           f"  Download: {d:.1f} Mbps" if d else f"  Download: falhou ({e1})",
           f"  Upload:   {u:.1f} Mbps" if u else f"  Upload:   falhou ({e2})"]
    if not u:
        out.append("\n  Dica: firewall, antivírus ou proxy podem estar a bloquear o envio para speed.cloudflare.com.")
    return "\n".join(out)


# ---------------------------------------------------------------- exportação
def full_text():
    parts = [f"FICTOR IT TOOLS - relatório {datetime.datetime.now():%Y-%m-%d %H:%M}\n"]
    if "sistema" not in REPORT:
        act_info()
    parts.append(fmt_info(REPORT["sistema"]))
    if "discos" not in REPORT:
        act_smart()
    parts.append(json.dumps(REPORT["discos"], indent=1, ensure_ascii=False))
    if "rede" in REPORT:
        parts.append(json.dumps(REPORT["rede"], indent=1, ensure_ascii=False))
    return "\n\n".join(parts)


def export(kind, p):
    txt = full_text()
    if kind == "json":
        json.dump({"gerado": str(datetime.datetime.now()), **REPORT}, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    elif kind == "html":
        import html
        open(p, "w", encoding="utf-8").write(f"<html><body style='background:#070d24;color:#7fd0ff;font-family:Consolas'><h1>Fictor IT Tools</h1><pre>{html.escape(txt)}</pre></body></html>")
    else:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(p, pagesize=A4)
        y = 800
        c.setFont("Courier", 8)
        for ln in txt.splitlines():
            if y < 40:
                c.showPage()
                c.setFont("Courier", 8)
                y = 800
            c.drawString(30, y, ln[:115].encode("latin-1", "replace").decode("latin-1"))
            y -= 10
        c.save()
    return f"Guardado: {p}"



RUNKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
DISKEY = r"Software\FictorITTools\Disabled"


def hive(n):
    return winreg.HKEY_CURRENT_USER if n == "HKCU" else winreg.HKEY_LOCAL_MACHINE


def list_startup():
    rows = []
    for h in ("HKCU", "HKLM"):
        for path, st in ((RUNKEY, "Ativo"), (DISKEY + "\\" + h, "Desativado")):
            try:
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER if st == "Desativado" else hive(h), path)
            except OSError:
                continue
            i = 0
            while True:
                try:
                    n, v, _ = winreg.EnumValue(k, i)
                    rows.append((h, n, v, st))
                    i += 1
                except OSError:
                    break
    return rows


def toggle_startup(row):
    h, n, v, st = row
    if st == "Ativo":
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, DISKEY + "\\" + h)
        winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
        winreg.DeleteValue(winreg.OpenKey(hive(h), RUNKEY, 0, winreg.KEY_SET_VALUE), n)
    else:
        k = winreg.OpenKey(hive(h), RUNKEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
        winreg.DeleteValue(winreg.OpenKey(winreg.HKEY_CURRENT_USER, DISKEY + "\\" + h, 0, winreg.KEY_SET_VALUE), n)



APPS = {"Google Chrome": "Google.Chrome", "Mozilla Firefox": "Mozilla.Firefox", "7-Zip": "7zip.7zip", "VLC": "VideoLAN.VLC",
        "Notepad++": "Notepad++.Notepad++", "VS Code": "Microsoft.VisualStudioCode", "CPU-Z": "CPUID.CPU-Z", "HWiNFO": "REALiX.HWiNFO",
        "CrystalDiskInfo": "CrystalDewWorld.CrystalDiskInfo", "CrystalDiskMark": "CrystalDewWorld.CrystalDiskMark", "GPU-Z": "TechPowerUp.GPU-Z",
        "LibreHardwareMonitor": "LibreHardwareMonitor.LibreHardwareMonitor", "Rufus": "Rufus.Rufus", "Ventoy": "Ventoy.Ventoy",
        "AnyDesk": "AnyDeskSoftwareGmbH.AnyDesk", "TeamViewer": "TeamViewer.TeamViewer", "Sysinternals": "Microsoft.Sysinternals.Suite",
        "WinDirStat": "WinDirStat.WinDirStat", "DDU": "Wagnardsoft.DisplayDriverUninstaller", "Malwarebytes": "Malwarebytes.Malwarebytes",
        "Everything": "voidtools.Everything", "PuTTY": "PuTTY.PuTTY", "Wireshark": "WiresharkFoundation.Wireshark"}



BLOAT = ["Microsoft.BingNews", "Microsoft.BingWeather", "Microsoft.GetHelp", "Microsoft.Getstarted", "Microsoft.MicrosoftSolitaireCollection",
         "Microsoft.WindowsFeedbackHub", "Microsoft.ZuneMusic", "Microsoft.ZuneVideo", "Microsoft.YourPhone", "MicrosoftTeams",
         "Clipchamp.Clipchamp", "Microsoft.MixedReality.Portal", "Microsoft.People", "Microsoft.SkypeApp", "king.com.CandyCrushSaga", "Microsoft.549981C3F5F10"]
DK = r"HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection"
TWEAKS = {"Desativar telemetria": f"New-Item '{DK}' -Force|Out-Null;Set-ItemProperty '{DK}' AllowTelemetry 0 -Type DWord",
          "Desativar serviço DiagTrack": "Stop-Service DiagTrack -Force;Set-Service DiagTrack -StartupType Disabled",
          "Desativar ID de publicidade": r"Set-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo' Enabled 0",
          "Desativar histórico de atividades": r"$k='HKLM:\SOFTWARE\Policies\Microsoft\Windows\System';New-Item $k -Force|Out-Null;Set-ItemProperty $k EnableActivityFeed 0;Set-ItemProperty $k PublishUserActivities 0"}



# ---------------------------------------------------------------- cartões estruturados
def info_cards(info):
    cards = []
    for sec, items in info.items():
        for i, it in enumerate(items):
            t = sec.upper() + (f" #{i + 1}" if len(items) > 1 else "")
            cards.append({"title": t, "rows": [[k, fmt_val(k, v)] for k, v in (it or {}).items()]})
    vm = psutil.virtual_memory()
    cards.append({"title": "LIVE", "rows": [["Núcleos físicos/lógicos", f"{psutil.cpu_count(False)}/{psutil.cpu_count()}"],
                  ["RAM total", f"{vm.total / 1024 ** 3:.1f} GB"], ["PC", platform.node()], ["Windows", platform.platform()]]})
    return {"cards": cards}


def act_info_cards():
    i = get_info()
    REPORT["sistema"] = i
    return info_cards(i)


def act_smart_cards():
    t = act_smart()
    d = REPORT.get("discos", {}).get("smart", [])
    if not d:
        return {"text": t}
    cards = []
    for x in d:
        cards.append({"title": x.get("Nome") or "Disco", "badge": str(x.get("Saude")),
                      "rows": [[k, fmt_val("Size", v) if k == "Tamanho" else v] for k, v in x.items() if k != "Nome"]})
    for p in REPORT["discos"].get("predict", []):
        cards.append({"title": "Previsão de falha", "badge": "FALHA!" if p.get("PredictFailure") else "OK", "rows": [["Disco", p.get("InstanceName")]]})
    return {"cards": cards}


ACTS = {"sistema": act_info_cards, "smart": act_smart_cards, "energia": act_power, "drivers": act_drivers, "wu": act_wu,
        "rede": act_net, "speed": act_speed, "sensores": act_sensors}
# ---------------------------------------------------------------- consumo (watts)
import collections
PWR = collections.deque(maxlen=150)   # 150 amostras x 2s = 5 minutos
PS_PWR = r'''
$o=[ordered]@{
lhm=@(Get-CimInstance -Namespace root/LibreHardwareMonitor -ClassName Sensor -EA SilentlyContinue|?{$_.SensorType -eq 'Power'}|Select Name,Identifier,Value)
bat=@(Get-CimInstance -Namespace root/wmi -ClassName BatteryStatus -EA SilentlyContinue|Select DischargeRate,ChargeRate,PowerOnline)
}
$o|ConvertTo-Json -Depth 3 -Compress
'''


def read_power():
    try:
        d = json.loads(ps(PS_PWR, timeout=20))
    except Exception:
        d = {}
    L = lambda x: x if isinstance(x, list) else ([x] if x else [])
    lhm, bat = L(d.get("lhm")), L(d.get("bat"))
    parts, cpu, gpu = [], 0.0, {}
    for s in lhm:
        i, n, v = (s.get("Identifier") or "").lower(), s.get("Name") or "", s.get("Value") or 0
        if "cpu" in i and "package" in n.lower():
            cpu += v
            parts.append(["CPU " + n, round(v, 1)])
        elif "/gpu" in i and ("power" in n.lower() or "package" in n.lower()):
            k = "/".join(i.split("/")[:3])
            gpu[k] = max(gpu.get(k, 0), v)
            parts.append(["GPU " + n, round(v, 1)])
    dis = max([b.get("DischargeRate") or 0 for b in bat] or [0]) / 1000
    if dis > 0:
        return dis, "Bateria: consumo total real do portátil", parts
    comp = cpu + sum(gpu.values())
    if comp > 0:
        return comp, "CPU + GPU (LibreHardwareMonitor). Não inclui restante hardware", parts
    est = 20 + psutil.cpu_percent(interval=None) * 0.9
    return est, "ESTIMATIVA pela carga do CPU (imprecisa). Abra o LibreHardwareMonitor para valores reais", parts


def power_loop():
    last = {"parts": []}
    while True:
        try:
            w, src, parts = read_power()
            PWR.append((time.time(), round(w, 1), src, parts))
        except Exception:
            pass
        time.sleep(1.5)


WIN = None


class Api:
    def __init__(self):
        self._log, self._busy = "", False
        threading.Thread(target=power_loop, daemon=True).start()

    def info(self):
        return {"admin": is_admin(), "pc": platform.node()}

    def run(self, name, arg=None):
        try:
            if name == "bottle":
                r = act_bottle(int(arg))()
            elif name == "vendor":
                webbrowser.open(VENDORS[arg])
                r = "Aberto: " + VENDORS[arg]
            else:
                r = ACTS[name]()
        except Exception as e:
            r = f"Erro: {e}"
        return r if isinstance(r, dict) else {"text": r}

    def power(self):
        h = list(PWR)
        if not h:
            return {"now": None, "hist": []}
        ws = [x[1] for x in h]
        return {"now": {"w": h[-1][1], "src": h[-1][2], "parts": h[-1][3]}, "hist": [[x[0], x[1]] for x in h],
                "avg": sum(ws) / len(ws), "min": min(ws), "max": max(ws)}

    def live(self):
        pc = psutil.cpu_percent(percpu=True, interval=0.4)
        c = psutil.cpu_freq()
        vm = psutil.virtual_memory()
        return {"cores": pc, "cpu": sum(pc) / len(pc), "mhz": c.current if c else 0, "ram": vm.percent,
                "ram_txt": f"{vm.used / 1024 ** 3:.1f} / {vm.total / 1024 ** 3:.1f} GB", "disk": psutil.disk_usage("C:\\").percent}

    def startup_list(self):
        return [{"h": h, "n": n, "v": v, "st": st} for h, n, v, st in list_startup()]

    def startup_toggle(self, h, n, v, st):
        try:
            toggle_startup((h, n, v, st))
            return "ok"
        except Exception as e:
            return f"{e} (HKLM precisa de administrador)"

    def apps_list(self):
        return APPS

    def job(self, verb, ids=None, query=""):
        if self._busy:
            return
        cmds = []
        if verb in ("install", "uninstall"):
            for pid in ids or []:
                c = ["winget", verb, "-e", "--id", pid]
                cmds.append(c + (["--accept-package-agreements", "--accept-source-agreements"] if verb == "install" else []))
        elif verb == "upgrade":
            cmds.append(["winget", "upgrade", "--all", "--accept-package-agreements", "--accept-source-agreements"])
        elif verb == "search":
            cmds.append(["winget", "search", query])
        self._log, self._busy = "", True

        def run():
            for c in cmds:
                self._log += ">> " + " ".join(c) + "\n"
                p = subprocess.Popen(c, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=NOWIN)
                for ln in p.stdout:
                    self._log += ln.decode("utf-8", "ignore")
                p.wait()
            self._log += "--- fim ---\n"
            self._busy = False
        threading.Thread(target=run, daemon=True).start()

    def poll(self, off):
        return {"text": self._log[off:], "len": len(self._log), "busy": self._busy}

    def debloat_items(self):
        return {"apps": BLOAT, "tweaks": list(TWEAKS)}

    def debloat_apply(self, names):
        if not is_admin():
            return "Execute a suite como administrador."
        out = []
        for n in names:
            cmd = TWEAKS.get(n) or f"Get-AppxPackage -AllUsers '*{n}*'|Remove-AppxPackage -AllUsers"
            out.append(f"[{n}] " + (ps(cmd) or "ok"))
        return "\n".join(out)

    def restore_point(self):
        return ps("Checkpoint-Computer -Description 'FictorITTools' -RestorePointType MODIFY_SETTINGS") or "Ponto de restauro criado."

    def export(self, kind):
        p = WIN.create_file_dialog(webview.SAVE_DIALOG, save_filename="relatorio." + kind)
        if not p:
            return "Cancelado."
        p = p[0] if isinstance(p, (list, tuple)) else p
        try:
            full_text()
            return export(kind, p)
        except Exception as e:
            return f"Erro: {e}"


def resource(p):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), p)


if __name__ == "__main__":
    WIN = webview.create_window("Fictor IT Tools - Aero Edition", resource("ui/index.html"), js_api=Api(),
                                width=1280, height=820, min_size=(1000, 650), background_color="#020b24")
    webview.start()
