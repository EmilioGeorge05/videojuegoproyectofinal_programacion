# ====================================================================
# PROYECTO FINAL DE PROGRAMACIÓN - VIDEOJUEGO DE COMBATE MULTIJUGADOR
# Entorno Oficial: Batallas del TEC
# Integrantes: Emilio George Esteva / Irving Uriel Silia Rodriguez
# ====================================================================

import os
import sys
import json
import queue
import socket
import sqlite3
import threading
import subprocess
import re
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# Directorios del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DB_PATH = os.path.join(BASE_DIR, "videojuegos.db")

# --------------------------------------------------------------------
# ESPECIFICACIONES OFICIALES DE PERSONAJES (DE LA PIZARRA)
# --------------------------------------------------------------------
ROLES_OFICIALES = {
    "Alumno Pelón": {
        "vida": 600,
        "ataque": 30,
        "defensa": 30,
        "velocidad": 15,
        "card": "card_pelon.png",
        "sprite": "sprite_pelon.png",
        "sprite_rival": "sprite_pelon_rival.png",
        "descripcion": "El tanque del salón. Enorme cantidad de vida y resistencia.",
        "icono": "🌱"
    },
    "Alumno Practicante": {
        "vida": 500,
        "ataque": 40,
        "defensa": 35,
        "velocidad": 20,
        "card": "card_practicante.png",
        "sprite": "sprite_practicante.png",
        "sprite_rival": "sprite_practicante_rival.png",
        "descripcion": "Primeros pasos laborales. Buena vida inicial y defensa sólida.",
        "icono": "⚙️"
    },
    "Alumno Residente": {
        "vida": 450,
        "ataque": 45,
        "defensa": 37,
        "velocidad": 22,
        "card": "card_residente.png",
        "sprite": "sprite_residente.png",
        "sprite_rival": "sprite_residente_rival.png",
        "descripcion": "Estancia profesional en empresa. Equilibrado y resistente.",
        "icono": "</>"
    },
    "Alumno Egresado": {
        "vida": 300,
        "ataque": 60,
        "defensa": 45,
        "velocidad": 30,
        "card": "card_egresado.png",
        "sprite": "sprite_egresado.png",
        "sprite_rival": "sprite_egresado_rival.png",
        "descripcion": "Graduado con honores. Balanceado, alto ataque y veloz.",
        "icono": "🎓"
    }
}

def normalizar_rol(rol_nombre):
    """Devuelve la clave canónica del rol oficial."""
    if not rol_nombre:
        return "Alumno Pelón"
    limpio = rol_nombre.lower().replace("ó", "o").strip()
    if "pelon" in limpio or "ingreso" in limpio:
        return "Alumno Pelón"
    elif "practicante" in limpio:
        return "Alumno Practicante"
    elif "residente" in limpio:
        return "Alumno Residente"
    elif "egresado" in limpio:
        return "Alumno Egresado"
    return "Alumno Pelón"


# --------------------------------------------------------------------
# CONFIGURACIÓN DE BASE DE DATOS SQLITE
# --------------------------------------------------------------------
def inicializar_bd():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT NOT NULL UNIQUE,
            correo TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS jugadores(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            apellido TEXT NOT NULL,
            personaje TEXT NOT NULL,
            vida INTEGER,
            ataque INTEGER,
            defensa INTEGER,
            velocidad INTEGER,
            bebio_caguama INTEGER DEFAULT 0,
            comio_algo INTEGER DEFAULT 0,
            vida_maxima INTEGER,
            usuario_id INTEGER DEFAULT 1
        )
    """)

    # Validar columnas
    cur.execute("PRAGMA table_info(jugadores)")
    cols = [c[1] for c in cur.fetchall()]
    if "comio_algo" not in cols:
        cur.execute("ALTER TABLE jugadores ADD COLUMN comio_algo INTEGER DEFAULT 0")
    if "usuario_id" not in cols:
        cur.execute("ALTER TABLE jugadores ADD COLUMN usuario_id INTEGER DEFAULT 1")

    # Si no hay usuarios en la BD, insertar usuarios iniciales para pruebas
    cur.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO usuarios (nombre_usuario, correo, contrasena)
            VALUES (?, ?, ?)
        """, ("alumno", "alumno@tec.mx", "1234"))
        cur.execute("""
            INSERT INTO usuarios (nombre_usuario, correo, contrasena)
            VALUES (?, ?, ?)
        """, ("profesor", "profesor@tec.mx", "1234"))

    conn.commit()
    conn.close()

inicializar_bd()


# --------------------------------------------------------------------
# CLASE MODELO DEL PERSONAJE
# --------------------------------------------------------------------
class Personaje:
    def __init__(self, nombre, apellido, personaje_tipo="Alumno Pelón",
                 vida=None, ataque=None, defensa=None, velocidad=None,
                 bebio_caguama=False, comio_algo=False, db_id=None):
        self.id = db_id
        self.nombre = str(nombre).strip()
        self.apellido = str(apellido).strip()
        self.personaje_tipo = normalizar_rol(personaje_tipo)

        stats_base = ROLES_OFICIALES[self.personaje_tipo]

        # La vida inicial se fija según el rol y NO es editable por el usuario
        self.vida_maxima = int(vida if vida is not None else stats_base["vida"])
        self.vida = int(self.vida_maxima)
        self.ataque = int(ataque if ataque is not None else stats_base["ataque"])
        self.defensa = int(defensa if defensa is not None else stats_base["defensa"])
        self.velocidad = int(velocidad if velocidad is not None else stats_base["velocidad"])

        self.bebio_caguama = bool(bebio_caguama)
        self.comio_algo = bool(comio_algo)

        # Estadísticas base para reintentar
        self.stats_originales = {
            "vida_maxima": stats_base["vida"],
            "ataque": stats_base["ataque"],
            "defensa": stats_base["defensa"],
            "velocidad": stats_base["velocidad"]
        }

    @property
    def porcentaje_vida(self):
        if self.vida_maxima <= 0:
            return 0
        return max(0, min(100, (self.vida / self.vida_maxima) * 100))

    @property
    def corazones(self):
        """
        Regla de especificación:
        100% vida: 5 corazones
        75-99%: 4 corazones
        50-74%: 3 corazones
        25-49%: 2 corazones
        1-24%: 1 corazón
        0%: 0 corazones (personaje morido)
        """
        if self.vida <= 0:
            return 0
        pct = self.porcentaje_vida
        if pct >= 100:
            return 5
        elif pct >= 75:
            return 4
        elif pct >= 50:
            return 3
        elif pct >= 25:
            return 2
        else:
            return 1

    @property
    def esta_vivo(self):
        return self.vida > 0

    def recibir_danio(self, cantidad):
        self.vida = max(0, self.vida - cantidad)
        return self.vida

    def curar_vida(self, cantidad):
        # Regla: Si tienes 100% de vida ya no excede el porcentaje aunque comas más
        anterior = self.vida
        self.vida = min(self.vida_maxima, self.vida + cantidad)
        return self.vida - anterior

    def revivir(self):
        self.vida = self.vida_maxima
        return self.vida

    def reiniciar_total(self):
        self.vida_maxima = self.stats_originales["vida_maxima"]
        self.vida = self.vida_maxima
        self.ataque = self.stats_originales["ataque"]
        self.defensa = self.stats_originales["defensa"]
        self.velocidad = self.stats_originales["velocidad"]
        self.bebio_caguama = False
        self.comio_algo = False

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "personaje_tipo": self.personaje_tipo,
            "vida": self.vida,
            "vida_maxima": self.vida_maxima,
            "ataque": self.ataque,
            "defensa": self.defensa,
            "velocidad": self.velocidad,
            "bebio_caguama": self.bebio_caguama,
            "comio_algo": self.comio_algo
        }

    @classmethod
    def from_dict(cls, d):
        p = cls(
            nombre=d.get("nombre", "Rival"),
            apellido=d.get("apellido", "Online"),
            personaje_tipo=d.get("personaje_tipo", "Alumno Egresado"),
            vida=d.get("vida_maxima", 300),
            ataque=d.get("ataque", 60),
            defensa=d.get("defensa", 45),
            velocidad=d.get("velocidad", 30),
            bebio_caguama=d.get("bebio_caguama", False),
            comio_algo=d.get("comio_algo", False),
            db_id=d.get("id", None)
        )
        p.vida = d.get("vida", p.vida_maxima)
        return p


# --------------------------------------------------------------------
# DETECCIÓN DE INTERFACES DE RED (MULTIJUGADOR ROBUSTO)
# --------------------------------------------------------------------
def obtener_ip_local():
    """Detecta la IP local preferida."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def detectar_interfaces_red():
    """
    Detecta todas las IPs de la máquina (Radmin VPN, Wi-Fi, Ethernet, etc.)
    Retorna una lista de tuplas: (descripcion, ip)
    """
    interfaces = []
    seen_ips = set()

    # 1. Analizar adaptadores mediante ipconfig en Windows
    try:
        salida = subprocess.check_output("ipconfig", text=True, encoding="cp850", errors="replace")
        nombre_actual = "Adaptador"
        for linea in salida.splitlines():
            linea_str = linea.strip()
            if "Adaptador" in linea_str or "adapter" in linea_str.lower():
                nombre_actual = linea_str.rstrip(":")
            elif "IPv4" in linea_str or ("Direcci" in linea_str and "IPv4" in linea_str):
                m = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", linea_str)
                if m:
                    ip = m.group(1)
                    if not ip.startswith("127.") and ip not in seen_ips:
                        seen_ips.add(ip)
                        if "radmin" in nombre_actual.lower():
                            desc = f"⭐ Radmin VPN ({ip}) [Recomendado para campus/escuela]"
                        elif "wi-fi" in nombre_actual.lower() or "inal" in nombre_actual.lower():
                            desc = f"📶 Wi-Fi Local ({ip})"
                        elif "ethernet" in nombre_actual.lower():
                            desc = f"🔌 Red Cableada / Ethernet ({ip})"
                        elif "tailscale" in nombre_actual.lower():
                            desc = f"🌐 Tailscale ({ip})"
                        else:
                            desc = f"💻 {nombre_actual} ({ip})"
                        interfaces.append((desc, ip))
    except Exception:
        pass

    # 2. Agregar IPs descubiertas por socket si faltaron
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and ip not in seen_ips:
                seen_ips.add(ip)
                if ip.startswith("26."):
                    desc = f"⭐ Radmin VPN ({ip}) [Recomendado para campus]"
                elif ip.startswith("192.168.") or ip.startswith("10."):
                    desc = f"📶 Red Local ({ip})"
                else:
                    desc = f"💻 IP ({ip})"
                interfaces.append((desc, ip))
    except Exception:
        pass

    # 3. Si no hay ninguna interfaz descubierta, usar la IP estándar
    if not interfaces:
        ip_def = obtener_ip_local()
        interfaces.append((f"IP Principal ({ip_def})", ip_def))

    # 4. Añadir siempre la opción localhost para pruebas en la misma máquina
    interfaces.append(("🖥️ Localhost (127.0.0.1) [Pruebas en esta misma PC]", "127.0.0.1"))
    return interfaces


# --------------------------------------------------------------------
# GESTOR DE RED (SOCKETS TCP MULTIJUGADOR)
# --------------------------------------------------------------------
class GestorRed:
    def __init__(self, cola_mensajes):
        self.cola = cola_mensajes
        self.socket_conexion = None
        self.socket_servidor = None
        self.hilo_red = None
        self.activo = False
        self.es_host = False

    def iniciar_servidor(self, puerto=5000):
        self.cerrar()
        self.es_host = True
        self.activo = True

        def hilo_servidor():
            try:
                self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket_servidor.bind(("0.0.0.0", int(puerto)))
                self.socket_servidor.listen(1)
                self.socket_servidor.settimeout(1.0)
                self.cola.put(("log", f"🟢 Servidor activo en puerto {puerto}. Esperando que el rival se conecte..."))

                while self.activo:
                    try:
                        conn, addr = self.socket_servidor.accept()
                        conn.settimeout(None)
                        self.socket_conexion = conn
                        self.cola.put(("conectado", {"host": True, "direccion": addr}))
                        self.escuchar_mensajes(conn)
                        break
                    except socket.timeout:
                        continue
                    except Exception as ex_acc:
                        if self.activo:
                            self.cola.put(("error", f"Error aceptando conexión: {ex_acc}"))
                        break
            except OSError as e:
                if self.activo:
                    if getattr(e, "winerror", None) == 10048 or "10048" in str(e):
                        self.cola.put(("error", f"El puerto {puerto} ya está en uso por otro programa o partida previa.\nIntenta con el puerto 5001 o 5002."))
                    else:
                        self.cola.put(("error", f"Error al abrir servidor en puerto {puerto}: {e}"))
            except Exception as e:
                if self.activo:
                    self.cola.put(("error", f"Error en servidor: {e}"))
            finally:
                if self.socket_servidor:
                    try:
                        self.socket_servidor.close()
                    except Exception:
                        pass
                self.socket_servidor = None

        self.hilo_red = threading.Thread(target=hilo_servidor, daemon=True)
        self.hilo_red.start()

    def conectar_cliente(self, ip_host, puerto=5000):
        self.cerrar()
        self.es_host = False
        self.activo = True

        def hilo_cliente():
            cli = None
            try:
                cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cli.settimeout(6.0) # 6 segundos de tiempo de espera
                self.cola.put(("log", f"🟡 Intentando conectar a {ip_host}:{puerto}..."))
                cli.connect((ip_host, int(puerto)))
                cli.settimeout(None)
                self.socket_conexion = cli
                self.cola.put(("conectado", {"host": False, "ip": ip_host}))
                self.escuchar_mensajes(cli)
            except socket.timeout:
                if self.activo:
                    msg = (
                        f"Tiempo de espera agotado al conectar a {ip_host}:{puerto}.\n\n"
                        "Posibles causas:\n"
                        "1) El Host aún no ha presionado 'INICIAR SALA Y ESPERAR RIVAL'.\n"
                        "2) Si están en Wi-Fi escolar (TEC), el router bloquea la conexión directa: usen Radmin VPN o Zona Wi-Fi móvil.\n"
                        "3) El Firewall de Windows del Host está bloqueando el puerto."
                    )
                    self.cola.put(("error", msg))
            except ConnectionRefusedError:
                if self.activo:
                    self.cola.put(("error", f"Conexión rechazada por {ip_host}:{puerto}.\nEl equipo rival está en línea pero no ha iniciado la sala en ese puerto."))
            except Exception as e:
                if self.activo:
                    self.cola.put(("error", f"No se pudo conectar a {ip_host}:{puerto} -> {e}"))
            finally:
                if not self.socket_conexion and cli:
                    try:
                        cli.close()
                    except Exception:
                        pass

        self.hilo_red = threading.Thread(target=hilo_cliente, daemon=True)
        self.hilo_red.start()

    def escuchar_mensajes(self, sock):
        buffer = ""
        while self.activo:
            try:
                datos = sock.recv(4096)
                if not datos:
                    self.cola.put(("desconectado", "El rival ha cerrado la conexión."))
                    break
                buffer += datos.decode("utf-8")
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    linea = linea.strip()
                    if linea:
                        obj = json.loads(linea)
                        self.cola.put(("mensaje", obj))
            except Exception as e:
                if self.activo:
                    self.cola.put(("desconectado", f"Pérdida de enlace de red: {e}"))
                break

    def enviar(self, datos_dict):
        if not self.socket_conexion:
            return False
        try:
            cadena = json.dumps(datos_dict) + "\n"
            self.socket_conexion.sendall(cadena.encode("utf-8"))
            return True
        except Exception as e:
            self.cola.put(("error", f"Error enviando datos: {e}"))
            return False

    def cerrar(self):
        self.activo = False
        if self.socket_conexion:
            try:
                self.socket_conexion.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.socket_conexion.close()
            except Exception:
                pass
            self.socket_conexion = None

        if self.socket_servidor:
            try:
                self.socket_servidor.close()
            except Exception:
                pass
            self.socket_servidor = None


# --------------------------------------------------------------------
# APLICACIÓN PRINCIPAL (TKINTER CON ENTORNO 'BATALLAS DEL TEC')
# --------------------------------------------------------------------
class VideojuegoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Batallas del TEC - Duelo de Alumnos (TCP/IP)")
        self.root.geometry("1100x740")
        self.root.configure(bg="#0E131F")
        self.root.resizable(False, False)

        # Cola de red
        self.cola_red = queue.Queue()
        self.gestor_red = GestorRed(self.cola_red)

        # Estado del juego
        self.es_multijugador = False
        self.mi_turno = False
        self.personaje_local = None
        self.personaje_rival = None

        # Datos del usuario logueado
        self.usuario_actual_id = 1
        self.usuario_actual_nombre = "alumno"
        self.usuario_actual_correo = "alumno@tec.mx"

        # Cargar assets gráficos
        self.imagenes = {}
        self.cargar_assets()

        # Cargar personaje inicial
        self.cargar_personaje_inicial()

        # Contenedor dinámico de pantallas
        self.contenedor = tk.Frame(self.root, bg="#0E131F")
        self.contenedor.pack(fill="both", expand=True)

        # Despachador de red
        self.root.after(100, self.procesar_eventos_red)

        # Iniciar directamente en pantalla de inicio de sesión
        self.pantalla_login()

    def cargar_personaje_inicial(self):
        """Carga el personaje asociado al usuario activo o el primero registrado."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nombre, apellido, personaje, vida, ataque, defensa, velocidad,
                   bebio_caguama, comio_algo, vida_maxima
            FROM jugadores
            WHERE usuario_id = ?
            LIMIT 1
        """, (self.usuario_actual_id,))
        row = cur.fetchone()

        if not row:
            # Buscar cualquier personaje existente
            cur.execute("""
                SELECT id, nombre, apellido, personaje, vida, ataque, defensa, velocidad,
                       bebio_caguama, comio_algo, vida_maxima
                FROM jugadores
                LIMIT 1
            """)
            row = cur.fetchone()
        conn.close()

        if row:
            self.personaje_local = Personaje(
                nombre=row[1],
                apellido=row[2],
                personaje_tipo=row[3],
                vida=row[4],
                ataque=row[5],
                defensa=row[6],
                velocidad=row[7],
                bebio_caguama=bool(row[8]),
                comio_algo=bool(row[9]),
                db_id=row[0]
            )
        else:
            self.personaje_local = Personaje(
                nombre="Emilio",
                apellido="George",
                personaje_tipo="Alumno Pelón"
            )

    def cargar_assets(self):
        """Carga los sprites, cartas y entorno del escenario."""
        sprites = {
            # Entorno de combate oficial 2.5D
            "arena_bg": ("arena_entorno_custom.png", (960, 420)),

            # Cartas completas de selección (Menú principal)
            "card_pelon": ("card_pelon.png", (220, 440)),
            "card_practicante": ("card_practicante.png", (220, 440)),
            "card_residente": ("card_residente.png", (220, 440)),
            "card_egresado": ("card_egresado.png", (220, 440)),

            # Miniaturas de cartas compactas para el creador de personajes
            "thumb_pelon": ("card_pelon.png", (125, 230)),
            "thumb_practicante": ("card_practicante.png", (125, 230)),
            "thumb_residente": ("card_residente.png", (125, 230)),
            "thumb_egresado": ("card_egresado.png", (125, 230)),

            # Sprites transparentes para la arena (Player 1 - mira a la derecha)
            "sprite_pelon": ("sprite_pelon.png", (135, 230)),
            "sprite_practicante": ("sprite_practicante.png", (145, 230)),
            "sprite_residente": ("sprite_residente.png", (135, 230)),
            "sprite_egresado": ("sprite_egresado.png", (145, 235)),

            # Sprites rival (Player 2 - espejados, miran a la izquierda)
            "sprite_pelon_rival": ("sprite_pelon_rival.png", (115, 195)),
            "sprite_practicante_rival": ("sprite_practicante_rival.png", (125, 195)),
            "sprite_residente_rival": ("sprite_residente_rival.png", (115, 195)),
            "sprite_egresado_rival": ("sprite_egresado_rival.png", (125, 200)),

            # Tienda y consumibles
            "panel_tienda": ("panel_tienda.png", (450, 240)),
            "atq_fuego": ("atq_fuego.png", (110, 110)),
            "atq_patada": ("atq_patada.png", (110, 110)),
            "atq_cachetada": ("atq_cachetada.png", (110, 110)),
            "atq_balazo": ("atq_balazo.png", (110, 110)),
            "cura_coca": ("cura_coca.png", (70, 80)),
            "cura_tamal": ("cura_tamal.png", (75, 80)),
            "cura_chilaquiles": ("cura_chilaquiles.png", (90, 80)),
            "cura_caguama": ("cura_caguama.png", (65, 80)),
            "cura_paracetamol": ("cura_paracetamol.png", (75, 80)),
            "personaje_derrotado": ("personaje_derrotado.png", (340, 200)),
        }

        for clave, (archivo, size) in sprites.items():
            ruta = os.path.join(ASSETS_DIR, archivo)
            if os.path.exists(ruta):
                try:
                    img = Image.open(ruta)
                    img = img.resize(size, Image.Resampling.LANCZOS)
                    self.imagenes[clave] = ImageTk.PhotoImage(img)
                except Exception as e:
                    print(f"Aviso al cargar {archivo}: {e}")
                    self.imagenes[clave] = None
            else:
                self.imagenes[clave] = None

    def limpiar_pantalla(self):
        for w in self.contenedor.winfo_children():
            w.destroy()

    def get_card_image(self, rol):
        rol_c = normalizar_rol(rol)
        if rol_c == "Alumno Pelón":
            return self.imagenes.get("card_pelon")
        elif rol_c == "Alumno Practicante":
            return self.imagenes.get("card_practicante")
        elif rol_c == "Alumno Residente":
            return self.imagenes.get("card_residente")
        elif rol_c == "Alumno Egresado":
            return self.imagenes.get("card_egresado")
        return None

    def get_card_thumb(self, rol):
        rol_c = normalizar_rol(rol)
        if rol_c == "Alumno Pelón":
            return self.imagenes.get("thumb_pelon")
        elif rol_c == "Alumno Practicante":
            return self.imagenes.get("thumb_practicante")
        elif rol_c == "Alumno Residente":
            return self.imagenes.get("thumb_residente")
        elif rol_c == "Alumno Egresado":
            return self.imagenes.get("thumb_egresado")
        return None

    def get_sprite_image(self, rol, es_rival=False):
        rol_c = normalizar_rol(rol)
        sufijo = "_rival" if es_rival else ""
        if rol_c == "Alumno Pelón":
            return self.imagenes.get(f"sprite_pelon{sufijo}")
        elif rol_c == "Alumno Practicante":
            return self.imagenes.get(f"sprite_practicante{sufijo}")
        elif rol_c == "Alumno Residente":
            return self.imagenes.get(f"sprite_residente{sufijo}")
        elif rol_c == "Alumno Egresado":
            return self.imagenes.get(f"sprite_egresado{sufijo}")
        return None


    # ================================================================
    # MANEJO DE EVENTOS DE RED
    # ================================================================
    def procesar_eventos_red(self):
        while not self.cola_red.empty():
            tipo, datos = self.cola_red.get_nowait()

            if tipo == "log":
                if hasattr(self, "lbl_estado_lobby") and self.lbl_estado_lobby.winfo_exists():
                    self.lbl_estado_lobby.config(text=str(datos), fg="#FFD166")

            elif tipo == "conectado":
                es_host = datos.get("host", False)
                paquete_inicial = {
                    "tipo": "handshake",
                    "personaje": self.personaje_local.to_dict(),
                    "host": es_host
                }
                self.gestor_red.enviar(paquete_inicial)
                self.mi_turno = es_host
                self.es_multijugador = True
                if hasattr(self, "lbl_estado_lobby") and self.lbl_estado_lobby.winfo_exists():
                    self.lbl_estado_lobby.config(text="¡Rival conectado! Sincronizando contrincantes...", fg="#06D6A0")

            elif tipo == "mensaje":
                self.manejar_mensaje_rival(datos)

            elif tipo == "desconectado":
                messagebox.showwarning("Conexión perdida", str(datos))
                self.es_multijugador = False
                self.pantalla_bienvenida()

            elif tipo == "error":
                messagebox.showerror("Error de red", str(datos))
                if hasattr(self, "lbl_estado_lobby") and self.lbl_estado_lobby.winfo_exists():
                    self.lbl_estado_lobby.config(text=f"❌ Error: {datos[:70]}...", fg="#FF5555")

        self.root.after(100, self.procesar_eventos_red)

    def manejar_mensaje_rival(self, datos):
        m_tipo = datos.get("tipo")

        if m_tipo == "handshake":
            datos_pj = datos.get("personaje")
            self.personaje_rival = Personaje.from_dict(datos_pj)
            self.pantalla_arena_combate()

        elif m_tipo == "accion_combate":
            subtipo = datos.get("subtipo")
            nombre_accion = datos.get("nombre")

            if subtipo == "ataque":
                danio = datos.get("danio", 0)
                self.personaje_local.recibir_danio(danio)
                self.mi_turno = True
                self.actualizar_hud_combate(f"💥 ¡El rival usó '{nombre_accion}' causándote {danio} de daño! Es tu turno.")

                if not self.personaje_local.esta_vivo:
                    self.pantalla_ko(ganador=self.personaje_rival, perdedor=self.personaje_local)

            elif subtipo == "curar":
                if self.personaje_rival:
                    self.personaje_rival.vida = datos.get("vida_rival", self.personaje_rival.vida)
                    self.personaje_rival.ataque = datos.get("ataque_rival", self.personaje_rival.ataque)
                    self.personaje_rival.defensa = datos.get("defensa_rival", self.personaje_rival.defensa)
                    self.personaje_rival.velocidad = datos.get("velocidad_rival", self.personaje_rival.velocidad)
                    self.personaje_rival.bebio_caguama = datos.get("bebio_caguama_rival", self.personaje_rival.bebio_caguama)
                self.mi_turno = True
                self.actualizar_hud_combate(f"🌮 ¡El rival consumió '{nombre_accion}' y restauró salud! Es tu turno.")

        elif m_tipo == "revancha":
            accion = datos.get("accion")
            if accion == "revivir":
                self.personaje_local.revivir()
                if self.personaje_rival:
                    self.personaje_rival.revivir()
                self.pantalla_arena_combate()
            elif accion == "reintentar":
                self.personaje_local.reiniciar_total()
                if self.personaje_rival:
                    self.personaje_rival.reiniciar_total()
                self.pantalla_arena_combate()


    # ================================================================
    # PANTALLA 0: INICIO DE SESIÓN Y REGISTRO DE USUARIO
    # ================================================================
    def pantalla_login(self, modo="login"):
        self.limpiar_pantalla()
        self.gestor_red.cerrar()
        self.es_multijugador = False

        cuerpo = tk.Frame(self.contenedor, bg="#0E131F")
        cuerpo.pack(fill="both", expand=True, padx=40, pady=25)

        # Encabezado
        tk.Label(
            cuerpo,
            text="BATALLAS DEL TEC - ARENA 1v1",
            font=("Impact", 36),
            fg="#00F0FF",
            bg="#0E131F"
        ).pack(pady=4)

        tk.Label(
            cuerpo,
            text="PROGRAMACIÓN 2 - PROYECTO FINAL",
            font=("Arial", 12, "bold"),
            fg="#FFD166",
            bg="#0E131F"
        ).pack(pady=2)

        # Tarjeta central
        card = tk.Frame(cuerpo, bg="#121826", bd=3, relief="ridge", highlightbackground="#00F0FF", highlightthickness=2)
        card.pack(pady=20, padx=100, fill="both", expand=True)

        if modo == "login":
            # --- VISTA DE INICIO DE SESIÓN ---
            tk.Label(card, text="🔑 INICIO DE SESIÓN DE ALUMNO", font=("Impact", 22), fg="#06D6A0", bg="#121826").pack(pady=(20, 5))
            tk.Label(card, text="Ingresa con tu usuario o correo registrado para acceder a tus personajes", font=("Arial", 10), fg="#A8DADC", bg="#121826").pack(pady=(0, 15))

            f_form = tk.Frame(card, bg="#121826")
            f_form.pack(pady=10)

            tk.Label(f_form, text="Nombre de Usuario o Correo:", font=("Arial", 11, "bold"), fg="white", bg="#121826").grid(row=0, column=0, sticky="w", pady=8, padx=10)
            ent_login_user = tk.Entry(f_form, font=("Arial", 12), width=28)
            ent_login_user.grid(row=0, column=1, pady=8, padx=10)
            ent_login_user.insert(0, "alumno")
            ent_login_user.focus()

            tk.Label(f_form, text="Contraseña:", font=("Arial", 11, "bold"), fg="white", bg="#121826").grid(row=1, column=0, sticky="w", pady=8, padx=10)
            ent_login_pass = tk.Entry(f_form, font=("Arial", 12), width=28, show="*")
            ent_login_pass.grid(row=1, column=1, pady=8, padx=10)
            ent_login_pass.insert(0, "1234")

            # Checkbox para ver contraseña
            var_ver_pass = tk.BooleanVar(value=False)
            def toggle_pass():
                ent_login_pass.config(show="" if var_ver_pass.get() else "*")
            chk_ver = tk.Checkbutton(f_form, text="Mostrar contraseña", variable=var_ver_pass, command=toggle_pass,
                                     bg="#121826", fg="#90E0EF", selectcolor="#182033", activebackground="#121826", activeforeground="#90E0EF")
            chk_ver.grid(row=2, column=1, sticky="w", padx=10)

            def accion_login(event=None):
                u_val = ent_login_user.get().strip()
                p_val = ent_login_pass.get().strip()

                if not u_val or not p_val:
                    messagebox.showwarning("Campos vacíos", "Por favor ingresa usuario y contraseña.")
                    return

                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, nombre_usuario, correo
                    FROM usuarios
                    WHERE (LOWER(nombre_usuario) = LOWER(?) OR LOWER(correo) = LOWER(?))
                      AND contrasena = ?
                """, (u_val, u_val, p_val))
                usuario = cur.fetchone()
                conn.close()

                if usuario:
                    self.usuario_actual_id = usuario[0]
                    self.usuario_actual_nombre = usuario[1]
                    self.usuario_actual_correo = usuario[2]
                    self.cargar_personaje_inicial()
                    messagebox.showinfo("¡Bienvenido!", f"¡Hola {self.usuario_actual_nombre}!\nSesión iniciada correctamente.")
                    self.pantalla_bienvenida()
                else:
                    messagebox.showerror("Error de autenticación", "Usuario, correo o contraseña incorrectos.\nSi no tienes cuenta, haz clic en 'Registrarse'.")

            ent_login_pass.bind("<Return>", accion_login)

            # Botones
            tk.Button(
                card,
                text="🚀 INICIAR SESIÓN",
                font=("Arial", 13, "bold"),
                bg="#06D6A0",
                fg="black",
                cursor="hand2",
                padx=25,
                pady=6,
                command=accion_login
            ).pack(pady=15)

            f_extras = tk.Frame(card, bg="#121826")
            f_extras.pack(pady=10)

            tk.Button(
                f_extras,
                text="📝 ¿No tienes cuenta? REGÍSTRATE AQUÍ",
                font=("Arial", 11, "bold"),
                bg="#1D3557",
                fg="white",
                cursor="hand2",
                padx=15,
                pady=5,
                command=lambda: self.pantalla_login(modo="registro")
            ).pack(side="left", padx=10)

            tk.Button(
                f_extras,
                text="⚡ MODO INVITADO",
                font=("Arial", 11),
                bg="#333333",
                fg="#FFD166",
                cursor="hand2",
                padx=12,
                pady=5,
                command=self.iniciar_modo_invitado
            ).pack(side="left", padx=10)

            tk.Label(card, text="💡 Usuario de prueba incluido: 'alumno' | Contraseña: '1234'", font=("Consolas", 10), fg="#88A0B8", bg="#121826").pack(pady=5)

        else:
            # --- VISTA DE REGISTRO DE NUEVO USUARIO ---
            tk.Label(card, text="📝 REGISTRO DE NUEVO ALUMNO", font=("Impact", 22), fg="#FFD166", bg="#121826").pack(pady=(15, 5))
            tk.Label(card, text="Crea tu cuenta oficial para guardar tus luchadores personalizados en la base de datos", font=("Arial", 10), fg="#A8DADC", bg="#121826").pack(pady=(0, 10))

            f_reg = tk.Frame(card, bg="#121826")
            f_reg.pack(pady=5)

            tk.Label(f_reg, text="Nombre de Usuario (Único):", font=("Arial", 11, "bold"), fg="white", bg="#121826").grid(row=0, column=0, sticky="w", pady=6, padx=10)
            ent_reg_user = tk.Entry(f_reg, font=("Arial", 11), width=28)
            ent_reg_user.grid(row=0, column=1, pady=6, padx=10)
            ent_reg_user.focus()

            tk.Label(f_reg, text="Correo Electrónico:", font=("Arial", 11, "bold"), fg="white", bg="#121826").grid(row=1, column=0, sticky="w", pady=6, padx=10)
            ent_reg_correo = tk.Entry(f_reg, font=("Arial", 11), width=28)
            ent_reg_correo.grid(row=1, column=1, pady=6, padx=10)
            ent_reg_correo.insert(0, "@tec.mx")

            tk.Label(f_reg, text="Contraseña:", font=("Arial", 11, "bold"), fg="white", bg="#121826").grid(row=2, column=0, sticky="w", pady=6, padx=10)
            ent_reg_pass1 = tk.Entry(f_reg, font=("Arial", 11), width=28, show="*")
            ent_reg_pass1.grid(row=2, column=1, pady=6, padx=10)

            tk.Label(f_reg, text="Confirmar Contraseña:", font=("Arial", 11, "bold"), fg="white", bg="#121826").grid(row=3, column=0, sticky="w", pady=6, padx=10)
            ent_reg_pass2 = tk.Entry(f_reg, font=("Arial", 11), width=28, show="*")
            ent_reg_pass2.grid(row=3, column=1, pady=6, padx=10)

            def accion_guardar_registro():
                nom = ent_reg_user.get().strip()
                cor = ent_reg_correo.get().strip()
                p1 = ent_reg_pass1.get().strip()
                p2 = ent_reg_pass2.get().strip()

                if not nom or not cor or not p1:
                    messagebox.showwarning("Datos incompletos", "Por favor completa todos los campos requeridos.")
                    return

                if p1 != p2:
                    messagebox.showerror("Error", "Las contraseñas no coinciden. Verifícalas.")
                    return

                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()

                # Verificar duplicados
                cur.execute("SELECT id FROM usuarios WHERE LOWER(nombre_usuario) = LOWER(?)", (nom,))
                if cur.fetchone():
                    conn.close()
                    messagebox.showerror("Usuario Duplicado", f"El nombre de usuario '{nom}' ya está registrado. Elige otro.")
                    return

                cur.execute("SELECT id FROM usuarios WHERE LOWER(correo) = LOWER(?)", (cor,))
                if cur.fetchone():
                    conn.close()
                    messagebox.showerror("Correo Duplicado", f"El correo '{cor}' ya está registrado con otra cuenta.")
                    return

                try:
                    cur.execute("""
                        INSERT INTO usuarios(nombre_usuario, correo, contrasena)
                        VALUES(?, ?, ?)
                    """, (nom, cor, p1))
                    conn.commit()
                    nuevo_id = cur.lastrowid
                    conn.close()

                    self.usuario_actual_id = nuevo_id
                    self.usuario_actual_nombre = nom
                    self.usuario_actual_correo = cor
                    self.cargar_personaje_inicial()
                    messagebox.showinfo("¡Registro Exitoso!", f"¡Cuenta '{nom}' creada correctamente!\nIniciando sesión...")
                    self.pantalla_bienvenida()

                except sqlite3.IntegrityError as err:
                    conn.close()
                    messagebox.showerror("Error de BD", f"No se pudo registrar el usuario: {err}")

            # Botones registro
            f_btns_reg = tk.Frame(card, bg="#121826")
            f_btns_reg.pack(pady=15)

            tk.Button(
                f_btns_reg,
                text="💾 CREAR MI CUENTA",
                font=("Arial", 12, "bold"),
                bg="#E76F51",
                fg="white",
                cursor="hand2",
                padx=20,
                pady=6,
                command=accion_guardar_registro
            ).pack(side="left", padx=10)

            tk.Button(
                f_btns_reg,
                text="🔙 REGRESAR A INICIAR SESIÓN",
                font=("Arial", 11, "bold"),
                bg="#333333",
                fg="white",
                cursor="hand2",
                padx=15,
                pady=6,
                command=lambda: self.pantalla_login(modo="login")
            ).pack(side="left", padx=10)

    def iniciar_modo_invitado(self):
        self.usuario_actual_id = 1
        self.usuario_actual_nombre = "Invitado"
        self.usuario_actual_correo = "invitado@tec.mx"
        self.cargar_personaje_inicial()
        self.pantalla_bienvenida()

    def cerrar_sesion(self):
        if messagebox.askyesno("Cerrar Sesión", "¿Seguro que deseas cerrar la sesión actual?"):
            self.usuario_actual_id = None
            self.usuario_actual_nombre = None
            self.usuario_actual_correo = None
            self.pantalla_login()


    # ================================================================
    # PANTALLA 1: MENÚ PRINCIPAL / BIENVENIDA
    # ================================================================
    def pantalla_bienvenida(self):
        self.limpiar_pantalla()
        self.gestor_red.cerrar()
        self.es_multijugador = False

        if not self.personaje_local:
            self.cargar_personaje_inicial()

        cuerpo = tk.Frame(self.contenedor, bg="#0E131F")
        cuerpo.pack(fill="both", expand=True, padx=40, pady=15)

        # Barra superior de sesión de usuario
        barra_usuario = tk.Frame(cuerpo, bg="#182033", bd=1, relief="solid")
        barra_usuario.pack(fill="x", pady=(0, 6), padx=5)

        tk.Label(
            barra_usuario,
            text=f"👤 Alumno en sesión: {self.usuario_actual_nombre} ({self.usuario_actual_correo})",
            font=("Arial", 10, "bold"),
            fg="#06D6A0",
            bg="#182033"
        ).pack(side="left", padx=15, pady=4)

        tk.Button(
            barra_usuario,
            text="🚪 Cerrar Sesión",
            font=("Arial", 9, "bold"),
            bg="#E63946",
            fg="white",
            cursor="hand2",
            padx=10,
            command=self.cerrar_sesion
        ).pack(side="right", padx=10, pady=2)

        tk.Label(
            cuerpo,
            text="BATALLAS DEL TEC - ARENA 1v1",
            font=("Impact", 34),
            fg="#00F0FF",
            bg="#0E131F"
        ).pack(pady=2)

        tk.Label(
            cuerpo,
            text=f"Luchador Activo: {self.personaje_local.nombre} {self.personaje_local.apellido} ({self.personaje_local.personaje_tipo})",
            font=("Consolas", 11, "bold"),
            fg="#FFD166",
            bg="#0E131F"
        ).pack(pady=4)

        centro = tk.Frame(cuerpo, bg="#0E131F")
        centro.pack(fill="both", expand=True, pady=6)

        # Lado izquierdo: Tarjeta oficial del personaje activo
        lado_izq = tk.Frame(centro, bg="#121826", bd=2, relief="groove")
        lado_izq.pack(side="left", fill="both", expand=True, padx=15, pady=5)

        tk.Label(lado_izq, text="TARJETA DEL ALUMNO", font=("Impact", 15), fg="#00F0FF", bg="#121826").pack(pady=8)
        img_card = self.get_card_image(self.personaje_local.personaje_tipo)
        if img_card:
            tk.Label(lado_izq, image=img_card, bg="#121826").pack(pady=5)
        else:
            tk.Label(lado_izq, text="🎓", font=("Segoe UI Emoji", 80), bg="#121826").pack(pady=40)

        # Lado derecho: Opciones principales
        lado_der = tk.Frame(centro, bg="#121826", bd=2, relief="groove")
        lado_der.pack(side="right", fill="both", expand=True, padx=15, pady=5)

        tk.Label(lado_der, text="MODOS DE JUEGO", font=("Impact", 22), fg="#E63946", bg="#121826").pack(pady=10)

        botones = [
            ("🌐 1. MODO MULTIJUGADOR EN RED (IP)", "#E63946", self.pantalla_lobby_online, "Combate por turnos sincronizados entre dos computadoras"),
            ("🥊 2. MODO PRÁCTICA LOCAL (1v1)", "#2A9D8F", self.iniciar_modo_practica, "Pruébalo en este mismo equipo contra un bot"),
            ("⚙️ 3. CREAR / CAMBIAR PERSONAJE", "#457B9D", self.pantalla_crear_personaje, "Crea y guarda luchadores en SQLite con vida oficial protegida"),
            ("📋 4. MOSTRAR INFORMACIÓN DEL LUCHADOR", "#1D3557", self.mostrar_info_personaje_local, "Revisa estadísticas detalladas y corazones"),
            ("🚪 5. SALIR", "#333333", self.root.quit, "Cerrar el videojuego")
        ]

        for texto, col, cmd, desc in botones:
            f_b = tk.Frame(lado_der, bg="#121826")
            f_b.pack(pady=5)
            b = tk.Button(f_b, text=texto, font=("Arial", 12, "bold"), bg=col, fg="white", cursor="hand2", width=34, command=cmd)
            b.pack()
            tk.Label(f_b, text=desc, font=("Arial", 8, "italic"), fg="#88A0B8", bg="#121826").pack()


    # ================================================================
    # PANTALLA 2: LOBBY MULTIJUGADOR (IP / SOCKETS MULTI-COMPUTADORA)
    # ================================================================
    def pantalla_lobby_online(self):
        self.limpiar_pantalla()
        self.gestor_red.cerrar()

        interfaces_disponibles = detectar_interfaces_red()
        ip_predeterminada = interfaces_disponibles[0][1] if interfaces_disponibles else "127.0.0.1"

        frame = tk.Frame(self.contenedor, bg="#121826", bd=3, relief="ridge", highlightbackground="#00F0FF", highlightthickness=2)
        frame.pack(fill="both", expand=True, padx=30, pady=15)

        # Barra superior con botón de regreso
        top_bar = tk.Frame(frame, bg="#121826")
        top_bar.pack(fill="x", padx=15, pady=(10, 2))

        tk.Label(top_bar, text="SALA DE JUEGO MULTIJUGADOR (TCP/IP)", font=("Impact", 24), fg="#00F0FF", bg="#121826").pack(side="left")
        tk.Button(
            top_bar,
            text="🔙 REGRESAR AL MENÚ PRINCIPAL",
            font=("Arial", 10, "bold"),
            bg="#333333",
            fg="white",
            cursor="hand2",
            padx=12,
            pady=4,
            command=self.pantalla_bienvenida
        ).pack(side="right")

        # Cartel explicativo de conexión entre computadoras
        banner_info = tk.Frame(frame, bg="#182033", bd=1, relief="solid")
        banner_info.pack(fill="x", padx=20, pady=6)
        txt_consejo = (
            "💡 CONSEJO PARA CONECTAR DOS COMPUTADORAS:\n"
            "• Si están en la red de la escuela (TEC), el Wi-Fi escolar BLOQUEA conexiones directas entre computadoras por seguridad.\n"
            "  -> SOLUCIÓN 1: Conéctense ambos a la misma red en Radmin VPN (usan la IP 26.x.x.x mostrada abajo).\n"
            "  -> SOLUCIÓN 2: Uno comparta 'Zona con cobertura móvil' (Hotspot) desde el celular y ambos se conectan a él.\n"
            "• Si el Firewall de Windows bloquea la conexión, haz clic en '🛡️ Ayuda con Firewall' abajo."
        )
        tk.Label(banner_info, text=txt_consejo, font=("Arial", 9), fg="#FFD166", bg="#182033", justify="left").pack(padx=12, pady=5)

        paneles = tk.Frame(frame, bg="#121826")
        paneles.pack(fill="both", expand=True, padx=20, pady=6)

        # --- COLUMNA 1: CREAR SALA (HOST / SERVIDOR) ---
        col_host = tk.Frame(paneles, bg="#182033", bd=2, relief="solid")
        col_host.pack(side="left", fill="both", expand=True, padx=8, pady=5)

        tk.Label(col_host, text="OPCIÓN A: CREAR SALA (HOST)", font=("Impact", 16), fg="#FFD166", bg="#182033").pack(pady=8)
        tk.Label(col_host, text="Tus Direcciones IP Disponibles:", font=("Arial", 10, "bold"), fg="white", bg="#182033").pack()

        # Selector de interfaz IP
        nombres_interfaces = [d[0] for d in interfaces_disponibles]
        combo_ips = ttk.Combobox(col_host, values=nombres_interfaces, state="readonly", font=("Arial", 9), width=38)
        combo_ips.pack(pady=4, padx=10)
        combo_ips.set(nombres_interfaces[0])

        lbl_ip_destacada = tk.Label(col_host, text=ip_predeterminada, font=("Consolas", 16, "bold"), fg="#06D6A0", bg="#182033")
        lbl_ip_destacada.pack(pady=4)

        def actualizar_ip_seleccionada(event=None):
            idx = combo_ips.current()
            if 0 <= idx < len(interfaces_disponibles):
                ip_elegida = interfaces_disponibles[idx][1]
                lbl_ip_destacada.config(text=ip_elegida)

        combo_ips.bind("<<ComboboxSelected>>", actualizar_ip_seleccionada)

        def copiar_ip():
            idx = combo_ips.current()
            if 0 <= idx < len(interfaces_disponibles):
                ip_elegida = interfaces_disponibles[idx][1]
                self.root.clipboard_clear()
                self.root.clipboard_append(ip_elegida)
                messagebox.showinfo("Copiado", f"IP '{ip_elegida}' copiada al portapapeles.\nPásasela a tu rival.")

        tk.Button(col_host, text="📋 Copiar IP al Portapapeles", font=("Arial", 9, "bold"), bg="#1D3557", fg="white", cursor="hand2", command=copiar_ip).pack(pady=2)

        f_port_host = tk.Frame(col_host, bg="#182033")
        f_port_host.pack(pady=6)
        tk.Label(f_port_host, text="Puerto TCP:", font=("Arial", 10, "bold"), fg="white", bg="#182033").pack(side="left", padx=5)
        ent_puerto_host = tk.Entry(f_port_host, font=("Consolas", 11), width=8, justify="center")
        ent_puerto_host.pack(side="left")
        ent_puerto_host.insert(0, "5000")

        def accion_iniciar_host():
            try:
                p_val = int(ent_puerto_host.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Puerto inválido. Ingresa un número (ej. 5000).")
                return
            self.lbl_estado_lobby.config(text=f"Servidor abierto en puerto {p_val}. Esperando al rival...", fg="#06D6A0")
            self.gestor_red.iniciar_servidor(p_val)

        tk.Button(col_host, text="🚀 INICIAR SALA Y ESPERAR RIVAL", font=("Arial", 11, "bold"), bg="#E76F51", fg="white", cursor="hand2", padx=12, pady=6, command=accion_iniciar_host).pack(pady=10)

        # --- COLUMNA 2: UNIRSE A SALA (CLIENTE) ---
        col_cli = tk.Frame(paneles, bg="#182033", bd=2, relief="solid")
        col_cli.pack(side="right", fill="both", expand=True, padx=8, pady=5)

        tk.Label(col_cli, text="OPCIÓN B: UNIRSE A SALA (CLIENTE)", font=("Impact", 16), fg="#00F0FF", bg="#182033").pack(pady=8)
        tk.Label(col_cli, text="Escribe la IP del Ordenador Host:", font=("Arial", 10, "bold"), fg="white", bg="#182033").pack(pady=2)

        f_entry_ip = tk.Frame(col_cli, bg="#182033")
        f_entry_ip.pack(pady=4)

        ent_ip = tk.Entry(f_entry_ip, font=("Consolas", 13), width=18, justify="center")
        ent_ip.pack(side="left", padx=4)
        ent_ip.insert(0, ip_predeterminada)

        def pegar_ip():
            try:
                texto = self.root.clipboard_get().strip()
                if texto:
                    ent_ip.delete(0, tk.END)
                    ent_ip.insert(0, texto)
            except Exception:
                pass
        tk.Button(f_entry_ip, text="📋 Pegar", font=("Arial", 9), bg="#2B3A4A", fg="white", cursor="hand2", command=pegar_ip).pack(side="left")

        f_port_cli = tk.Frame(col_cli, bg="#182033")
        f_port_cli.pack(pady=6)
        tk.Label(f_port_cli, text="Puerto:", font=("Arial", 10, "bold"), fg="white", bg="#182033").pack(side="left", padx=5)
        ent_puerto_cli = tk.Entry(f_port_cli, font=("Consolas", 11), width=8, justify="center")
        ent_puerto_cli.pack(side="left")
        ent_puerto_cli.insert(0, "5000")

        def accion_conectar():
            ip_val = ent_ip.get().strip()
            if not ip_val:
                messagebox.showerror("Error", "Debes ingresar la dirección IP del rival.")
                return
            try:
                p_val = int(ent_puerto_cli.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Puerto inválido.")
                return
            self.lbl_estado_lobby.config(text=f"🟡 Conectando a {ip_val}:{p_val}...", fg="#FFD166")
            self.gestor_red.conectar_cliente(ip_val, p_val)

        tk.Button(col_cli, text="🔗 CONECTARSE AL HOST", font=("Arial", 11, "bold"), bg="#06D6A0", fg="black", cursor="hand2", padx=14, pady=6, command=accion_conectar).pack(pady=10)

        # Estado y Navegación inferior
        self.lbl_estado_lobby = tk.Label(frame, text="Listo para conectar. Elige si vas a ser Host o Cliente.", font=("Arial", 11, "bold"), fg="#FFD166", bg="#121826")
        self.lbl_estado_lobby.pack(pady=4)

        f_acciones_inferiores = tk.Frame(frame, bg="#121826")
        f_acciones_inferiores.pack(pady=6)

        def abrir_guia_firewall():
            msg = (
                "🛡️ CONFIGURACIÓN DE FIREWALL Y RED:\n\n"
                "1. Si Windows bloquea las conexiones entrantes al Host, puedes ejecutar el script:\n"
                "   'Habilitar_Firewall_Multijugador.bat' que se encuentra en la carpeta del juego.\n"
                "   (Haz clic derecho -> 'Ejecutar como administrador').\n\n"
                "2. Si están en el campus TEC / Universidad:\n"
                "   Las redes escolares tienen 'Aislamiento de AP' que impide que dos PCs se comuniquen.\n"
                "   Para solucionarlo, usen Radmin VPN (ambos en la misma red) o conéctense a la Zona Wi-Fi de un teléfono celular.\n\n"
                "¿Deseas abrir la carpeta del juego para ver el script de Firewall?"
            )
            if messagebox.askyesno("Ayuda con Firewall", msg):
                try:
                    os.startfile(BASE_DIR)
                except Exception:
                    pass

        tk.Button(f_acciones_inferiores, text="🛡️ Ayuda con Firewall / Red", font=("Arial", 10, "bold"), bg="#1D3557", fg="#FFD166", cursor="hand2", padx=12, pady=4, command=abrir_guia_firewall).pack(side="left", padx=8)
        tk.Button(f_acciones_inferiores, text="🔙 REGRESAR AL MENÚ PRINCIPAL", font=("Arial", 11, "bold"), bg="#333333", fg="white", cursor="hand2", padx=18, pady=4, command=self.pantalla_bienvenida).pack(side="left", padx=8)


    # ================================================================
    # PANTALLA 3: CREACIÓN Y SELECCIÓN DE PERSONAJES
    # ================================================================
    def pantalla_crear_personaje(self):
        self.limpiar_pantalla()

        frame = tk.Frame(self.contenedor, bg="#121826", bd=3, relief="ridge", highlightbackground="#E63946", highlightthickness=2)
        frame.pack(fill="both", expand=True, padx=25, pady=10)

        # Barra superior con título y botón de retorno directo
        top_bar = tk.Frame(frame, bg="#121826")
        top_bar.pack(fill="x", padx=15, pady=(8, 2))

        tk.Label(top_bar, text="CREACIÓN Y ADMINISTRACIÓN DE PERSONAJES", font=("Impact", 22), fg="#E63946", bg="#121826").pack(side="left")

        # BOTÓN SUPERIOR PARA REGRESAR AL MENÚ PRINCIPAL
        tk.Button(
            top_bar,
            text="🔙 REGRESAR AL MENÚ PRINCIPAL",
            font=("Arial", 10, "bold"),
            bg="#333333",
            fg="white",
            cursor="hand2",
            padx=14,
            pady=4,
            command=self.pantalla_bienvenida
        ).pack(side="right")

        tk.Label(
            frame,
            text="* La vida inicial está protegida y fijada por el rol oficial de la pizarra. No se puede modificar.",
            font=("Arial", 9, "italic"),
            fg="#A8DADC",
            bg="#121826"
        ).pack(pady=(0, 6))

        cuerpo = tk.Frame(frame, bg="#121826")
        cuerpo.pack(fill="both", expand=True, padx=10, pady=2)

        # --- PANEL IZQUIERDO: FORMULARIO DE NUEVO PERSONAJE ---
        form_frame = tk.Frame(cuerpo, bg="#182033", bd=2, relief="solid")
        form_frame.pack(side="left", fill="both", expand=True, padx=8, pady=4)

        tk.Label(form_frame, text="➕ CREAR NUEVO PERSONAJE", font=("Impact", 13), fg="#FFD166", bg="#182033").pack(pady=(6, 2))

        f_form_interior = tk.Frame(form_frame, bg="#182033")
        f_form_interior.pack(fill="both", expand=True, padx=10, pady=2)

        # Columna de campos
        f_grid = tk.Frame(f_form_interior, bg="#182033")
        f_grid.pack(side="left", fill="both", expand=True, padx=5, pady=2)

        tk.Label(f_grid, text="Nombre (Único):", font=("Arial", 10, "bold"), fg="white", bg="#182033").grid(row=0, column=0, sticky="w", pady=4)
        ent_nombre = tk.Entry(f_grid, font=("Arial", 10), width=18)
        ent_nombre.grid(row=0, column=1, pady=4, padx=6)
        ent_nombre.insert(0, "Luchador")

        tk.Label(f_grid, text="Apellido:", font=("Arial", 10, "bold"), fg="white", bg="#182033").grid(row=1, column=0, sticky="w", pady=4)
        ent_apellido = tk.Entry(f_grid, font=("Arial", 10), width=18)
        ent_apellido.grid(row=1, column=1, pady=4, padx=6)
        ent_apellido.insert(0, "TEC")

        tk.Label(f_grid, text="Rol Oficial:", font=("Arial", 10, "bold"), fg="white", bg="#182033").grid(row=2, column=0, sticky="w", pady=4)
        roles_disponibles = list(ROLES_OFICIALES.keys())
        combo_rol = ttk.Combobox(f_grid, values=roles_disponibles, state="readonly", font=("Arial", 9), width=16)
        combo_rol.grid(row=2, column=1, pady=4, padx=6)
        combo_rol.set(roles_disponibles[0])

        tk.Label(f_grid, text="Vida Inicial:", font=("Arial", 10, "bold"), fg="#06D6A0", bg="#182033").grid(row=3, column=0, sticky="w", pady=4)
        lbl_vida_val = tk.Label(f_grid, text="600 PV (🔒 Bloqueada)", font=("Consolas", 10, "bold"), fg="#06D6A0", bg="#182033")
        lbl_vida_val.grid(row=3, column=1, sticky="w", pady=4, padx=6)

        tk.Label(f_grid, text="Estadísticas:", font=("Arial", 10, "bold"), fg="#90E0EF", bg="#182033").grid(row=4, column=0, sticky="w", pady=4)
        lbl_stats_val = tk.Label(f_grid, text="ATQ: 30 | DEF: 30 | VEL: 15", font=("Consolas", 9, "bold"), fg="#90E0EF", bg="#182033")
        lbl_stats_val.grid(row=4, column=1, sticky="w", pady=4, padx=6)

        # Columna de vista previa compacta (tarjeta)
        f_preview = tk.Frame(f_form_interior, bg="#182033")
        f_preview.pack(side="right", padx=5, pady=2)
        lbl_preview = tk.Label(f_preview, bg="#182033")
        lbl_preview.pack()

        def actualizar_preview(event=None):
            rol_sel = combo_rol.get()
            datos_rol = ROLES_OFICIALES[rol_sel]
            lbl_vida_val.config(text=f"{datos_rol['vida']} PV (🔒 Bloqueada)")
            lbl_stats_val.config(text=f"ATQ:{datos_rol['ataque']} DEF:{datos_rol['defensa']} VEL:{datos_rol['velocidad']}")
            img_c = self.get_card_thumb(rol_sel)
            if img_c:
                lbl_preview.config(image=img_c, text="")
            else:
                lbl_preview.config(image="", text="🎓", font=("Segoe UI Emoji", 40), fg="white")

        combo_rol.bind("<<ComboboxSelected>>", actualizar_preview)
        actualizar_preview()

        # BOTÓN PRINCIPAL REQUERIDO: CREAR Y AGREGAR A LA LISTA DE GUARDADOS
        f_form_botones = tk.Frame(form_frame, bg="#182033")
        f_form_botones.pack(pady=8)

        def accion_crear_personaje():
            nom = ent_nombre.get().strip()
            ape = ent_apellido.get().strip()
            rol = combo_rol.get()

            if not nom or not ape:
                messagebox.showerror("Error", "Ingresa tanto el nombre como el apellido.")
                return

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT id FROM jugadores WHERE LOWER(nombre) = LOWER(?)", (nom,))
            if cur.fetchone():
                conn.close()
                messagebox.showerror("Nombre Duplicado", f"El nombre '{nom}' ya existe. Debe ser único.")
                return

            st = ROLES_OFICIALES[rol]
            cur.execute("""
                INSERT INTO jugadores(
                    nombre, apellido, personaje, vida, ataque, defensa, velocidad,
                    bebio_caguama, comio_algo, vida_maxima, usuario_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
            """, (nom, ape, rol, st["vida"], st["ataque"], st["defensa"], st["velocidad"], st["vida"], self.usuario_actual_id))
            conn.commit()
            nuevo_id = cur.lastrowid
            conn.close()

            # Activar el nuevo personaje como el actual
            self.personaje_local = Personaje(nombre=nom, apellido=ape, personaje_tipo=rol, db_id=nuevo_id)
            messagebox.showinfo("¡Guardado!", f"¡Personaje '{nom} {ape}' creado con éxito y añadido a la lista de guardados!")
            self.pantalla_crear_personaje()

        tk.Button(
            f_form_botones,
            text="➕ CREAR Y GUARDAR PERSONAJE",
            font=("Arial", 11, "bold"),
            bg="#06D6A0",
            fg="black",
            cursor="hand2",
            padx=14,
            pady=5,
            command=accion_crear_personaje
        ).pack(side="left", padx=5)

        def limpiar_campos():
            ent_nombre.delete(0, tk.END)
            ent_apellido.delete(0, tk.END)

        tk.Button(
            f_form_botones,
            text="🧹 Limpiar",
            font=("Arial", 10),
            bg="#37474F",
            fg="white",
            cursor="hand2",
            padx=8,
            pady=4,
            command=limpiar_campos
        ).pack(side="left", padx=5)

        # --- PANEL DERECHO: LISTA DE PERSONAJES GUARDADOS ---
        lista_frame = tk.Frame(cuerpo, bg="#182033", bd=2, relief="solid")
        lista_frame.pack(side="right", fill="both", expand=True, padx=8, pady=4)

        tk.Label(lista_frame, text="📋 PERSONAJES GUARDADOS EN BASE DE DATOS", font=("Impact", 13), fg="#00F0FF", bg="#182033").pack(pady=(6, 2))

        cols = ("ID", "Nombre", "Apellido", "Rol", "Vida", "ATQ", "DEF", "VEL", "Dueño")
        tree = ttk.Treeview(lista_frame, columns=cols, show="headings", height=8)
        self.tree_personajes = tree
        for c in cols:
            tree.heading(c, text=c)
            w_col = 40 if c in ("ID", "Vida", "ATQ", "DEF", "VEL") else 85
            tree.column(c, width=w_col, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=4)

        # Llenar tabla con personajes y nombre de usuario dueño
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT j.id, j.nombre, j.apellido, j.personaje, j.vida, j.ataque, j.defensa, j.velocidad,
                   j.vida_maxima, COALESCE(u.nombre_usuario, 'General')
            FROM jugadores j
            LEFT JOIN usuarios u ON j.usuario_id = u.id
            ORDER BY j.id DESC
        """)
        rows = cur.fetchall()
        conn.close()

        for r in rows:
            tree.insert("", "end", values=(r[0], r[1], r[2], r[3], f"{r[4]}/{r[8]}", r[5], r[6], r[7], r[9]))

        def cargar_sel():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Aviso", "Selecciona un personaje de la lista.")
                return
            id_sel = tree.item(sel[0])["values"][0]
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                SELECT id, nombre, apellido, personaje, vida, ataque, defensa, velocidad,
                       bebio_caguama, comio_algo, vida_maxima
                FROM jugadores
                WHERE id = ?
            """, (id_sel,))
            d = cur.fetchone()
            conn.close()
            if d:
                self.personaje_local = Personaje(
                    nombre=d[1],
                    apellido=d[2],
                    personaje_tipo=d[3],
                    vida=d[4],
                    ataque=d[5],
                    defensa=d[6],
                    velocidad=d[7],
                    bebio_caguama=bool(d[8]),
                    comio_algo=bool(d[9]),
                    db_id=d[0]
                )
                messagebox.showinfo("Luchador Activo", f"¡'{self.personaje_local.nombre} {self.personaje_local.apellido}' seleccionado como tu luchador activo!")
                self.pantalla_bienvenida()

        def eliminar_sel():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Aviso", "Selecciona el personaje que deseas eliminar.")
                return
            id_sel = tree.item(sel[0])["values"][0]
            nom_sel = tree.item(sel[0])["values"][1]
            if messagebox.askyesno("Confirmar Eliminación", f"¿Seguro que deseas eliminar a '{nom_sel}' (ID {id_sel}) de la base de datos?"):
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("DELETE FROM jugadores WHERE id = ?", (id_sel,))
                conn.commit()
                conn.close()
                self.pantalla_crear_personaje()

        btn_box = tk.Frame(lista_frame, bg="#182033")
        btn_box.pack(pady=6)
        tk.Button(btn_box, text="✅ USAR COMO LUCHADOR ACTIVO", font=("Arial", 10, "bold"), bg="#06D6A0", fg="black", cursor="hand2", padx=10, pady=3, command=cargar_sel).pack(side="left", padx=5)
        tk.Button(btn_box, text="🗑️ ELIMINAR", font=("Arial", 10, "bold"), bg="#E63946", fg="white", cursor="hand2", padx=10, pady=3, command=eliminar_sel).pack(side="left", padx=5)

        # BOTÓN INFERIOR PARA REGRESAR AL MENÚ PRINCIPAL
        f_bot = tk.Frame(frame, bg="#121826")
        f_bot.pack(fill="x", pady=(4, 6))
        tk.Button(
            f_bot,
            text="🔙 REGRESAR AL MENÚ PRINCIPAL",
            font=("Arial", 11, "bold"),
            bg="#333333",
            fg="white",
            cursor="hand2",
            padx=20,
            pady=5,
            command=self.pantalla_bienvenida
        ).pack()


    # ================================================================
    # PANTALLA 4: ARENA DE COMBATE 2.5D ('BATALLAS DEL TEC')
    # ================================================================
    def iniciar_modo_practica(self):
        self.es_multijugador = False
        self.mi_turno = True
        self.personaje_rival = Personaje(
            nombre="MIGUEL",
            apellido="HERRERA",
            personaje_tipo="Alumno Egresado"
        )
        self.pantalla_arena_combate()

    def pantalla_arena_combate(self):
        self.limpiar_pantalla()

        p1 = self.personaje_local
        p2 = self.personaje_rival if self.personaje_rival else Personaje("Rival", "Online", "Alumno Egresado")

        contenedor_combate = tk.Frame(self.contenedor, bg="#0E131F")
        contenedor_combate.pack(fill="both", expand=True, padx=20, pady=8)

        # ------------------------------------------------------------
        # 1. CANVAS SUPERIOR: ESCENARIO 2.5D
        # ------------------------------------------------------------
        canvas_w, canvas_h = 960, 420
        self.canvas_arena = tk.Canvas(
            contenedor_combate,
            width=canvas_w,
            height=canvas_h,
            bg="#121826",
            highlightthickness=2,
            highlightbackground="#5A6B8C"
        )
        self.canvas_arena.pack(pady=4)

        # Fondo oficial
        if self.imagenes.get("arena_bg"):
            self.canvas_arena.create_image(0, 0, image=self.imagenes["arena_bg"], anchor="nw")

        # Pedestal Rival (Superior Derecho) en (700, 210)
        img_sprite_p2 = self.get_sprite_image(p2.personaje_tipo, es_rival=True)
        if img_sprite_p2:
            self.id_sprite_p2 = self.canvas_arena.create_image(700, 210, image=img_sprite_p2, anchor="center")
        else:
            self.id_sprite_p2 = self.canvas_arena.create_text(700, 210, text="🎓", font=("Segoe UI Emoji", 60))

        # Etiqueta de nombre flotante Rival
        self.canvas_arena.create_text(
            700, 95,
            text=f"{p2.nombre}".upper(),
            font=("Arial", 11, "bold"),
            fill="#FFFFFF"
        )

        # Pedestal Jugador 1 (Inferior Izquierdo) en (250, 305)
        img_sprite_p1 = self.get_sprite_image(p1.personaje_tipo, es_rival=False)
        if img_sprite_p1:
            self.id_sprite_p1 = self.canvas_arena.create_image(250, 305, image=img_sprite_p1, anchor="center")
        else:
            self.id_sprite_p1 = self.canvas_arena.create_text(250, 305, text="🧑‍🎓", font=("Segoe UI Emoji", 70))

        # Etiqueta de nombre flotante Jugador 1
        self.canvas_arena.create_text(
            250, 180,
            text=f"{p1.nombre}".lower(),
            font=("Consolas", 12, "bold"),
            fill="#FFD166"
        )

        # HUD SUPERIOR DERECHO: DATOS DEL RIVAL
        hud_rx1, hud_ry1, hud_rx2, hud_ry2 = 620, 14, 945, 78
        self.canvas_arena.create_rectangle(
            hud_rx1, hud_ry1, hud_rx2, hud_ry2,
            fill="#141E34",
            outline="#8B9DC3",
            width=2
        )
        self.id_hud_p2_nom = self.canvas_arena.create_text(
            hud_rx1 + 12, hud_ry1 + 18,
            text=f"{p2.nombre} {p2.apellido}".upper(),
            font=("Arial", 11, "bold"),
            fill="#FFFFFF",
            anchor="w"
        )
        self.id_hud_p2_rol = self.canvas_arena.create_text(
            hud_rx2 - 12, hud_ry1 + 18,
            text=f"{p2.personaje_tipo}",
            font=("Arial", 10, "italic"),
            fill="#C0D0F0",
            anchor="e"
        )

        # Barra de vida Rival
        bar_x1, bar_y1, bar_x2, bar_y2 = hud_rx1 + 12, hud_ry1 + 38, hud_rx2 - 12, hud_ry1 + 52
        self.canvas_arena.create_rectangle(bar_x1, bar_y1, bar_x2, bar_y2, fill="#3A1C24", outline="#506080", width=1)
        pct_p2 = p2.porcentaje_vida
        fill_w_p2 = int((bar_x2 - bar_x1) * (pct_p2 / 100.0))
        self.id_bar_p2 = self.canvas_arena.create_rectangle(bar_x1, bar_y1, bar_x1 + fill_w_p2, bar_y2, fill="#2ECC71", outline="")
        self.id_txt_bar_p2 = self.canvas_arena.create_text(
            bar_x2 - 5, bar_y1 + 7,
            text=f"{p2.vida} / {p2.vida_maxima}",
            font=("Consolas", 9, "bold"),
            fill="#FFFFFF",
            anchor="e"
        )

        # ------------------------------------------------------------
        # 2. PANEL DE CONTROL INFERIOR
        # ------------------------------------------------------------
        self.frame_bottom = tk.Frame(contenedor_combate, bg="#12182B", bd=2, relief="ridge", highlightbackground="#8B9DC3", highlightthickness=2)
        self.frame_bottom.pack(fill="x", pady=4, padx=5)

        # Fila 1: Turno
        texto_turno = "🟢 Tu turno... ¡Elige una jugada!" if self.mi_turno else "⏳ Turno del rival... Esperando su jugada..."
        col_turno = "#F4D03F" if self.mi_turno else "#E74C3C"
        self.lbl_turno_txt = tk.Label(
            self.frame_bottom,
            text=texto_turno,
            font=("Arial", 13, "bold"),
            fg=col_turno,
            bg="#12182B"
        )
        self.lbl_turno_txt.pack(anchor="w", padx=20, pady=(6, 2))

        # Fila 2: Estadísticas del Alumno
        p1_stats_str = f"{p1.personaje_tipo}   ATQ: {p1.ataque:.2f}   DEF: {p1.defensa:.2f}   VEL: {p1.velocidad:.2f}   |   🍺 Caguama: {'SÍ' if p1.bebio_caguama else 'NO'}"
        self.lbl_stats_local = tk.Label(
            self.frame_bottom,
            text=p1_stats_str,
            font=("Consolas", 11, "bold"),
            fg="#90CAF9",
            bg="#12182B"
        )
        self.lbl_stats_local.pack(anchor="w", padx=20, pady=1)

        # Fila 3: Barra de vida del Jugador 1
        f_vida_row = tk.Frame(self.frame_bottom, bg="#12182B")
        f_vida_row.pack(anchor="w", padx=20, pady=3, fill="x")

        self.cv_hp_local = tk.Canvas(f_vida_row, width=320, height=18, bg="#2C3E50", highlightthickness=1, highlightbackground="#506080")
        self.cv_hp_local.pack(side="left")
        self.id_fill_p1 = self.cv_hp_local.create_rectangle(0, 0, int(320 * (p1.porcentaje_vida / 100.0)), 18, fill="#2ECC71", outline="")

        self.lbl_hp_num_local = tk.Label(
            f_vida_row,
            text=f"Vida {p1.vida} / {p1.vida_maxima}  ({p1.corazones} corazones)",
            font=("Consolas", 11, "bold"),
            fg="#FFFFFF",
            bg="#12182B"
        )
        self.lbl_hp_num_local.pack(side="left", padx=15)

        # Fila 4: Subestado / Log
        self.lbl_sublog = tk.Label(
            self.frame_bottom,
            text="Esperando su jugada..." if not self.mi_turno else "Selecciona una acción de combate:",
            font=("Arial", 10, "italic"),
            fg="#A0B8D0",
            bg="#12182B"
        )
        self.lbl_sublog.pack(anchor="w", padx=20, pady=(1, 6))

        # Fila 5: Botones de Acción
        f_botones_row = tk.Frame(self.frame_bottom, bg="#12182B")
        f_botones_row.pack(fill="x", padx=20, pady=(2, 8))

        self.btn_atacar = tk.Button(
            f_botones_row,
            text="⚔️ MENÚ DE ATAQUE",
            font=("Arial", 11, "bold"),
            bg="#D9534F",
            fg="white",
            cursor="hand2",
            padx=14,
            pady=3,
            command=self.pantalla_menu_ataque
        )
        self.btn_atacar.pack(side="left", padx=5)

        self.btn_curar = tk.Button(
            f_botones_row,
            text="🌮 MENÚ CURAR (TIENDA)",
            font=("Arial", 11, "bold"),
            bg="#2A9D8F",
            fg="white",
            cursor="hand2",
            padx=14,
            pady=3,
            command=self.pantalla_tienda_curar
        )
        self.btn_curar.pack(side="left", padx=5)

        tk.Button(
            f_botones_row,
            text="📋 VER INFO COMPLETA",
            font=("Arial", 10),
            bg="#457B9D",
            fg="white",
            cursor="hand2",
            padx=12,
            pady=3,
            command=self.mostrar_info_personaje_local
        ).pack(side="left", padx=5)

        tk.Button(
            f_botones_row,
            text="🔙 VOLVER AL MENÚ",
            font=("Arial", 10),
            bg="#37474F",
            fg="white",
            cursor="hand2",
            padx=12,
            pady=3,
            command=self.pantalla_bienvenida
        ).pack(side="right", padx=5)

        self.actualizar_hud_combate()

    def actualizar_hud_combate(self, mensaje_log=None):
        p1 = self.personaje_local
        p2 = self.personaje_rival

        # Actualizar HUD Rival
        if hasattr(self, "canvas_arena") and self.canvas_arena.winfo_exists() and p2:
            pct_p2 = p2.porcentaje_vida
            bar_w = int((309) * (pct_p2 / 100.0))
            self.canvas_arena.coords(self.id_bar_p2, 632, 52, 632 + bar_w, 66)
            self.canvas_arena.itemconfig(self.id_txt_bar_p2, text=f"{p2.vida} / {p2.vida_maxima}")
            self.canvas_arena.itemconfig(self.id_hud_p2_nom, text=f"{p2.nombre} {p2.apellido}".upper())
            self.canvas_arena.itemconfig(self.id_hud_p2_rol, text=f"{p2.personaje_tipo}")

        # Actualizar HUD Local
        if hasattr(self, "frame_bottom") and self.frame_bottom.winfo_exists():
            texto_turno = "🟢 ¡Tu turno! Elige una jugada..." if self.mi_turno else "⏳ Turno del rival... Esperando jugada..."
            col_turno = "#F4D03F" if self.mi_turno else "#E74C3C"
            self.lbl_turno_txt.config(text=texto_turno, fg=col_turno)

            p1_stats_str = f"{p1.personaje_tipo}   ATQ: {p1.ataque:.2f}   DEF: {p1.defensa:.2f}   VEL: {p1.velocidad:.2f}   |   🍺 Caguama: {'SÍ' if p1.bebio_caguama else 'NO'}"
            self.lbl_stats_local.config(text=p1_stats_str)

            self.cv_hp_local.coords(self.id_fill_p1, 0, 0, int(320 * (p1.porcentaje_vida / 100.0)), 18)
            self.lbl_hp_num_local.config(text=f"Vida {p1.vida} / {p1.vida_maxima}  ({p1.corazones} corazones)")

            if mensaje_log:
                self.lbl_sublog.config(text=mensaje_log, fg="#FFD166")
            else:
                self.lbl_sublog.config(
                    text="Selecciona tu acción de combate:" if self.mi_turno else "Esperando su jugada...",
                    fg="#A0B8D0"
                )

            st = "normal" if self.mi_turno else "disabled"
            self.btn_atacar.config(state=st)
            self.btn_curar.config(state=st)


    # ================================================================
    # PANTALLA 5: MENÚ DE ATAQUE
    # ================================================================
    def pantalla_menu_ataque(self):
        if not self.mi_turno:
            messagebox.showinfo("Aviso", "No es tu turno de atacar.")
            return

        self.limpiar_pantalla()

        frame = tk.Frame(self.contenedor, bg="#121826", bd=3, relief="ridge", highlightbackground="#E63946", highlightthickness=2)
        frame.pack(fill="both", expand=True, padx=40, pady=20)

        tk.Label(frame, text="SELECCIONA UN ATAQUE PARA LANZAR", font=("Impact", 24), fg="#E63946", bg="#121826").pack(pady=10)

        p = self.personaje_local
        tk.Label(
            frame,
            text=f"Luchador: {p.nombre} {p.apellido} ({p.personaje_tipo}) | Tu Vida: {p.vida}/{p.vida_maxima} ({int(p.porcentaje_vida)}%) | Caguama: {'SÍ' if p.bebio_caguama else 'NO'}",
            font=("Arial", 11, "bold"),
            fg="#FFD166",
            bg="#121826"
        ).pack(pady=4)

        grid_frame = tk.Frame(frame, bg="#121826")
        grid_frame.pack(pady=15)

        # 1. Escupitajo de fuego (-50 PV)
        f1 = tk.Frame(grid_frame, bg="#182033", bd=2, relief="solid")
        f1.grid(row=0, column=0, padx=15, pady=10)
        if self.imagenes.get("atq_fuego"):
            tk.Button(f1, image=self.imagenes["atq_fuego"], bg="#182033", bd=0, cursor="hand2",
                      command=lambda: self.ejecutar_ataque("Escupitajo de fuego", 50)).pack(padx=8, pady=5)
        else:
            tk.Button(f1, text="🔥 Escupitajo de fuego\n(-50 PV)", font=("Arial", 11, "bold"), bg="#E63946", fg="white",
                      width=18, height=3, cursor="hand2", command=lambda: self.ejecutar_ataque("Escupitajo de fuego", 50)).pack(padx=8, pady=5)
        tk.Label(f1, text="1. Escupitajo (-50 PV)", font=("Arial", 10, "bold"), fg="white", bg="#182033").pack(pady=3)

        # 2. Patada fuerte (-80 PV)
        f2 = tk.Frame(grid_frame, bg="#182033", bd=2, relief="solid")
        f2.grid(row=0, column=1, padx=15, pady=10)
        if self.imagenes.get("atq_patada"):
            tk.Button(f2, image=self.imagenes["atq_patada"], bg="#182033", bd=0, cursor="hand2",
                      command=lambda: self.ejecutar_ataque("Patada fuerte", 80)).pack(padx=8, pady=5)
        else:
            tk.Button(f2, text="👟 Patada fuerte\n(-80 PV)", font=("Arial", 11, "bold"), bg="#D90429", fg="white",
                      width=18, height=3, cursor="hand2", command=lambda: self.ejecutar_ataque("Patada fuerte", 80)).pack(padx=8, pady=5)
        tk.Label(f2, text="2. Patada (-80 PV)", font=("Arial", 10, "bold"), fg="white", bg="#182033").pack(pady=3)

        # 3. Cachetada guajolotera (-120 PV)
        f3 = tk.Frame(grid_frame, bg="#182033", bd=2, relief="solid")
        f3.grid(row=1, column=0, padx=15, pady=10)
        if self.imagenes.get("atq_cachetada"):
            tk.Button(f3, image=self.imagenes["atq_cachetada"], bg="#182033", bd=0, cursor="hand2",
                      command=lambda: self.ejecutar_ataque("Cachetada guajolotera", 120)).pack(padx=8, pady=5)
        else:
            tk.Button(f3, text="👋 Cachetada guajolotera\n(-120 PV)", font=("Arial", 11, "bold"), bg="#9D0208", fg="white",
                      width=18, height=3, cursor="hand2", command=lambda: self.ejecutar_ataque("Cachetada guajolotera", 120)).pack(padx=8, pady=5)
        tk.Label(f3, text="3. Cachetada (-120 PV)", font=("Arial", 10, "bold"), fg="white", bg="#182033").pack(pady=3)

        # 4. Balazo a la mollera (-100 PV)
        puede_balazo = (p.porcentaje_vida <= 30) and p.bebio_caguama
        f4 = tk.Frame(grid_frame, bg="#182033", bd=2, relief="solid")
        f4.grid(row=1, column=1, padx=15, pady=10)

        if self.imagenes.get("atq_balazo"):
            tk.Button(f4, image=self.imagenes["atq_balazo"], bg="#182033", bd=0, cursor="hand2",
                      command=lambda: self.intentar_balazo_mollera()).pack(padx=8, pady=5)
        else:
            candado_txt = "" if puede_balazo else "🔒 [BLOQUEADO]\n"
            tk.Button(f4, text=f"{candado_txt}💥 Balazo mollera\n(-100 PV)", font=("Arial", 11, "bold"),
                      bg="#6A040F" if puede_balazo else "#370617", fg="white", width=18, height=3, cursor="hand2",
                      command=lambda: self.intentar_balazo_mollera()).pack(padx=8, pady=5)

        status_balazo = "✅ DESBLOQUEADO (-100)" if puede_balazo else "🔒 BLOQUEADO (≤30% vida + 🍺)"
        tk.Label(f4, text=status_balazo, font=("Arial", 9, "bold"), fg="#06D6A0" if puede_balazo else "#E63946", bg="#182033").pack(pady=3)

        tk.Button(frame, text="🔙 REGRESAR A LA ARENA", font=("Arial", 12, "bold"), bg="#333333", fg="white", cursor="hand2", padx=20, pady=6, command=self.pantalla_arena_combate).pack(pady=15)

    def intentar_balazo_mollera(self):
        p = self.personaje_local
        if p.porcentaje_vida > 30 and not p.bebio_caguama:
            messagebox.showwarning(
                "¡Ataque Bloqueado! 🔒",
                f"No puedes usar 'Balazo a la mollera'.\n\nRequiere DOS condiciones:\n"
                f"1. Tener 30% o menos de vida (tienes {int(p.porcentaje_vida)}%).\n"
                "2. Haber tomado una caguama previamente en la tienda."
            )
            return

        if p.porcentaje_vida > 30:
            messagebox.showwarning(
                "¡Ataque Bloqueado! 🔒",
                f"Tu vida está al {int(p.porcentaje_vida)}%.\nDebes tener 30% de vida o menos para desatar este ataque de desesperación."
            )
            return

        if not p.bebio_caguama:
            messagebox.showwarning(
                "¡Ataque Bloqueado! 🔒",
                "¡No has tomado ninguna caguama!\nDebes ir a la tienda de curación y tomarte una caguama para desbloquear el valor."
            )
            return

        self.ejecutar_ataque("Balazo a la mollera", 100)

    def ejecutar_ataque(self, nombre_ataque, danio):
        p_rival = self.personaje_rival

        if p_rival:
            p_rival.recibir_danio(danio)

        if self.es_multijugador:
            paquete = {
                "tipo": "accion_combate",
                "subtipo": "ataque",
                "nombre": nombre_ataque,
                "danio": danio
            }
            self.gestor_red.enviar(paquete)

        self.mi_turno = False
        self.pantalla_arena_combate()
        self.actualizar_hud_combate(f"💥 ¡Lanzaste '{nombre_ataque}' causando {danio} de daño al rival!")

        if p_rival and not p_rival.esta_vivo:
            self.pantalla_ko(ganador=self.personaje_local, perdedor=p_rival)
            return

        if not self.es_multijugador:
            self.root.after(1000, self.turno_simulado_bot)

    def turno_simulado_bot(self):
        if not self.personaje_rival or not self.personaje_rival.esta_vivo:
            return

        danio = 50
        nom = "Escupitajo de fuego"
        self.personaje_local.recibir_danio(danio)
        self.mi_turno = True
        self.actualizar_hud_combate(f"🤖 El rival contratacó con '{nom}' haciéndote {danio} de daño. ¡Tu turno!")

        if not self.personaje_local.esta_vivo:
            self.pantalla_ko(ganador=self.personaje_rival, perdedor=self.personaje_local)


    # ================================================================
    # PANTALLA 6: TIENDA DE CURACIÓN (TAQUERÍA)
    # ================================================================
    def pantalla_tienda_curar(self):
        if not self.mi_turno:
            messagebox.showinfo("Aviso", "No es tu turno.")
            return

        self.limpiar_pantalla()

        frame = tk.Frame(self.contenedor, bg="#121826", bd=3, relief="ridge", highlightbackground="#2A9D8F", highlightthickness=2)
        frame.pack(fill="both", expand=True, padx=40, pady=15)

        tk.Label(frame, text="🌮 TAQUERÍA Y PUESTO DE CURACIÓN 🌮", font=("Impact", 24), fg="#FFD166", bg="#121826").pack(pady=8)

        p = self.personaje_local
        tk.Label(
            frame,
            text=f"Cliente: {p.nombre} {p.apellido} | Vida: {p.vida}/{p.vida_maxima} ({int(p.porcentaje_vida)}%) | Comida previa: {'SÍ' if p.comio_algo else 'NO (Panza vacía)'}",
            font=("Arial", 11, "bold"),
            fg="#00F0FF",
            bg="#121826"
        ).pack(pady=4)

        cuerpo = tk.Frame(frame, bg="#121826")
        cuerpo.pack(fill="both", expand=True, padx=15, pady=5)

        lado_izq = tk.Frame(cuerpo, bg="#182033", bd=2, relief="solid")
        lado_izq.pack(side="left", fill="both", expand=True, padx=10, pady=5)

        if self.imagenes.get("panel_tienda"):
            tk.Label(lado_izq, image=self.imagenes["panel_tienda"], bg="#182033").pack(pady=10)
        else:
            tk.Label(lado_izq, text="🏪🌮🍺", font=("Segoe UI Emoji", 60), bg="#182033").pack(pady=40)

        tk.Label(
            lado_izq,
            text="¡Bienvenido a la taquería! Consume alimentos para tener panza llena y curarte.",
            font=("Arial", 10, "bold"),
            fg="#06D6A0",
            bg="#182033",
            wraplength=300,
            justify="center"
        ).pack(pady=10)

        lado_der = tk.Frame(cuerpo, bg="#182033", bd=2, relief="solid")
        lado_der.pack(side="right", fill="both", expand=True, padx=10, pady=5)

        items = [
            ("1. Coca Cola Light", "+10 PV | -5% todas las stats", self.imagenes.get("cura_coca"), self.curar_coca),
            ("2. Tamal de Mole", "+10% Vida | -10% Velocidad", self.imagenes.get("cura_tamal"), self.curar_tamal),
            ("3. Chilaquiles Verdes", "+50% Vida inicial | +5% todas las stats", self.imagenes.get("cura_chilaquiles"), self.curar_chilaquiles),
            ("4. Caguama", "+15% Vida | Velocidad a la mitad (50%)", self.imagenes.get("cura_caguama"), self.curar_caguama),
            ("5. Paracetamol", "+100% Vida (Full) | -1% todas las stats", self.imagenes.get("cura_paracetamol"), self.curar_paracetamol)
        ]

        for nombre, desc, img, cmd in items:
            row_f = tk.Frame(lado_der, bg="#121826", bd=1, relief="solid")
            row_f.pack(fill="x", padx=10, pady=3)

            if img:
                tk.Label(row_f, image=img, bg="#121826").pack(side="left", padx=5)

            t_f = tk.Frame(row_f, bg="#121826")
            t_f.pack(side="left", padx=8, fill="x", expand=True)

            tk.Label(t_f, text=nombre, font=("Arial", 10, "bold"), fg="white", bg="#121826").pack(anchor="w")
            tk.Label(t_f, text=desc, font=("Arial", 8), fg="#90E0EF", bg="#121826").pack(anchor="w")

            tk.Button(row_f, text="CONSUMIR", font=("Arial", 9, "bold"), bg="#E76F51", fg="white", cursor="hand2", padx=8, command=cmd).pack(side="right", padx=10, pady=4)

        tk.Button(frame, text="🔙 REGRESAR A LA ARENA", font=("Arial", 11, "bold"), bg="#333333", fg="white", cursor="hand2", padx=20, pady=5, command=self.pantalla_arena_combate).pack(pady=8)

    def verificar_tope_vida(self):
        p = self.personaje_local
        if p.vida >= p.vida_maxima:
            messagebox.showinfo("Vida Completa", "¡Ya tienes el 100% de vida! Aunque consumas más, tu vida no excederá el límite de salud.")

    def sincronizar_curacion_red(self, nombre_item):
        p = self.personaje_local
        if self.es_multijugador:
            paquete = {
                "tipo": "accion_combate",
                "subtipo": "curar",
                "nombre": nombre_item,
                "vida_rival": p.vida,
                "ataque_rival": p.ataque,
                "defensa_rival": p.defensa,
                "velocidad_rival": p.velocidad,
                "bebio_caguama_rival": p.bebio_caguama
            }
            self.gestor_red.enviar(paquete)

        self.mi_turno = False
        self.pantalla_arena_combate()
        self.actualizar_hud_combate(f"🌮 Consumiste '{nombre_item}'. Vida actual: {p.vida}/{p.vida_maxima}.")

        if not self.es_multijugador:
            self.root.after(1000, self.turno_simulado_bot)

    def curar_coca(self):
        p = self.personaje_local
        self.verificar_tope_vida()
        p.curar_vida(10)
        p.ataque = max(1, int(p.ataque * 0.95))
        p.defensa = max(1, int(p.defensa * 0.95))
        p.velocidad = max(1, int(p.velocidad * 0.95))
        p.comio_algo = True
        self.sincronizar_curacion_red("Coca Cola Light")

    def curar_tamal(self):
        p = self.personaje_local
        self.verificar_tope_vida()
        aumento = int(p.vida_maxima * 0.10)
        p.curar_vida(aumento)
        p.velocidad = max(1, int(p.velocidad * 0.90))
        p.comio_algo = True
        self.sincronizar_curacion_red("Tamal de Mole")

    def curar_chilaquiles(self):
        p = self.personaje_local
        self.verificar_tope_vida()
        aumento = int(p.stats_originales["vida_maxima"] * 0.50)
        p.curar_vida(aumento)
        p.ataque = int(p.ataque * 1.05)
        p.defensa = int(p.defensa * 1.05)
        p.velocidad = int(p.velocidad * 1.05)
        p.comio_algo = True
        self.sincronizar_curacion_red("Chilaquiles Verdes")

    def curar_caguama(self):
        p = self.personaje_local
        if not p.comio_algo:
            messagebox.showwarning(
                "¡Alerta de Caguama en ayunas! 🍺⚠️",
                "¡No has comido nada previamente!\nSi te tomas la caguama con la panza vacía se te va a subir rápido.\n¡Échate primero un tamal de mole o unos chilaquiles verdes!"
            )
            return

        self.verificar_tope_vida()
        aumento = int(p.vida_maxima * 0.15)
        p.curar_vida(aumento)
        p.velocidad = max(1, int(p.velocidad * 0.50))
        p.bebio_caguama = True
        self.sincronizar_curacion_red("Caguama")

    def curar_paracetamol(self):
        p = self.personaje_local
        p.vida = p.vida_maxima
        p.ataque = max(1, int(p.ataque * 0.99))
        p.defensa = max(1, int(p.defensa * 0.99))
        p.velocidad = max(1, int(p.velocidad * 0.99))
        p.comio_algo = True
        self.sincronizar_curacion_red("Paracetamol")


    # ================================================================
    # PANTALLA 7: KO / DERROTA / VICTORIA
    # ================================================================
    def pantalla_ko(self, ganador, perdedor):
        self.limpiar_pantalla()

        frame = tk.Frame(self.contenedor, bg="#0B090A", bd=3, relief="solid")
        frame.pack(fill="both", expand=True, padx=40, pady=20)

        es_mi_victoria = (ganador == self.personaje_local)
        titulo_txt = "🏆 ¡VICTORIA EN COMBATE! 🏆" if es_mi_victoria else "💀 PERSONAJE MORIDO (KO) 💀"
        titulo_col = "#06D6A0" if es_mi_victoria else "#E63946"

        tk.Label(frame, text=titulo_txt, font=("Impact", 34), fg=titulo_col, bg="#0B090A").pack(pady=10)

        tk.Label(
            frame,
            text=f"Ganador: {ganador.nombre} {ganador.apellido} ({ganador.personaje_tipo})\nPerdedor: {perdedor.nombre} {perdedor.apellido} cayó en la banqueta.",
            font=("Arial", 13, "bold"),
            fg="#FFD166",
            bg="#0B090A",
            justify="center"
        ).pack(pady=5)

        tk.Label(frame, text="🖤 🖤 🖤 🖤 🖤 (0 Corazones)", font=("Segoe UI Emoji", 18), fg="#FF0055", bg="#0B090A").pack()

        if self.imagenes.get("personaje_derrotado"):
            tk.Label(frame, image=self.imagenes["personaje_derrotado"], bg="#0B090A").pack(pady=8)
        else:
            tk.Label(frame, text="😵💫🍺", font=("Segoe UI Emoji", 60), bg="#0B090A").pack(pady=20)

        btn_box = tk.Frame(frame, bg="#0B090A")
        btn_box.pack(pady=15)

        def accion_revivir():
            if self.es_multijugador:
                self.gestor_red.enviar({"tipo": "revancha", "accion": "revivir"})
            self.personaje_local.revivir()
            if self.personaje_rival:
                self.personaje_rival.revivir()
            self.mi_turno = True
            self.pantalla_arena_combate()

        def accion_reintentar():
            if self.es_multijugador:
                self.gestor_red.enviar({"tipo": "revancha", "accion": "reintentar"})
            self.personaje_local.reiniciar_total()
            if self.personaje_rival:
                self.personaje_rival.reiniciar_total()
            self.mi_turno = True
            self.pantalla_arena_combate()

        tk.Button(btn_box, text="💚 REVIVIR (100% VIDA)", font=("Impact", 15), bg="#06D6A0", fg="black", cursor="hand2", padx=20, pady=6, command=accion_revivir).pack(side="left", padx=10)
        tk.Button(btn_box, text="🔄 ¿REINTENTAR?", font=("Impact", 15), bg="#00B4D8", fg="black", cursor="hand2", padx=20, pady=6, command=accion_reintentar).pack(side="left", padx=10)
        tk.Button(btn_box, text="🔙 MENÚ PRINCIPAL", font=("Arial", 12, "bold"), bg="#333333", fg="white", cursor="hand2", padx=15, pady=6, command=self.pantalla_bienvenida).pack(side="left", padx=10)


    # ================================================================
    # INFORMACIÓN DETALLADA DEL LUCHADOR
    # ================================================================
    def mostrar_info_personaje_local(self):
        p = self.personaje_local
        info = (
            f"=== FICHA TÉCNICA DEL ALUMNO ===\n\n"
            f"• Nombre completo: {p.nombre} {p.apellido}\n"
            f"• Rol oficial: {p.personaje_tipo}\n"
            f"• Estado de combate: {'VIVO ✅' if p.esta_vivo else '💀 MORIDO (0 Corazones)'}\n"
            f"• Corazones activos: {p.corazones} / 5 corazones\n"
            f"• Puntos de Vida: {p.vida} / {p.vida_maxima} ({int(p.porcentaje_vida)}%)\n\n"
            f"• Puntos de Ataque: {p.ataque} pts\n"
            f"• Puntos de Defensa: {p.defensa} pts\n"
            f"• Puntos de Velocidad: {p.velocidad} pts\n\n"
            f"• ¿Tomó Caguama?: {'SÍ (Desbloquea Balazo a la mollera)' if p.bebio_caguama else 'NO'}\n"
            f"• ¿Comió previamente?: {'SÍ (Estómago listo)' if p.comio_algo else 'NO (Panza vacía)'}\n"
        )
        messagebox.showinfo(f"Ficha: {p.nombre} {p.apellido}", info)


# --------------------------------------------------------------------
# PUNTO DE ENTRADA PRINCIPAL
# --------------------------------------------------------------------
if __name__ == "__main__":
    ventana = tk.Tk()
    app = VideojuegoApp(ventana)
    ventana.mainloop()
