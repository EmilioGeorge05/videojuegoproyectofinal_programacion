#emilio george esteva
#irving uriel silia rodriguez

import sqlite3
conexion = sqlite3.connect("videojuegos.db")#abre la conexión con la base de datos. Si videojuego.db no existe, SQLite lo crea
print("BASE DE DATOS UTILIZADA:", conexion.execute("PRAGMA database_list").fetchone()[2])
cursor = conexion.cursor()#nos permite ejecutar instrucciones para crear tablas, guardar datos y consultar información
import tkinter as tk
import socket
import threading
import json

partida_activa = False
jugador_conectado = None

cursor.execute("""
CREATE TABLE IF NOT EXISTS jugadores(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    apellido TEXT NOT NULL,
    personaje TEXT NOT NULL,
    vida INTEGER,
    ataque INTEGER,
    defensa INTEGER,
    velocidad INTEGER,
    bebio_caguama INTEGER,
    vida_maxima INTEGER
)



""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario TEXT NOT NULL UNIQUE,
    correo TEXT NOT NULL UNIQUE,
    contrasena TEXT NOT NULL
)
""")


cursor.execute("PRAGMA table_info(jugadores)")
columnas = cursor.fetchall()

if "usuario_id" not in [columna[1] for columna in columnas]:
    cursor.execute("""
        ALTER TABLE jugadores
        ADD COLUMN usuario_id INTEGER
    """)

conexion.commit()

if "usuario_id" not in [columna[1] for columna in columnas]:
    cursor.execute("""
        ALTER TABLE jugadores
        ADD COLUMN usuario_id INTEGER
    """)


def registrar_usuario():
    print("\n=== REGISTRO DE USUARIO ===")

    nombre_usuario = input("Crea tu nombre de usuario: ")
    correo = input("Escribe tu correo: ")
    contrasena = input("Crea tu contraseña: ")

    try:
        cursor.execute("""
            INSERT INTO usuarios(nombre_usuario, correo, contrasena)
            VALUES(?, ?, ?)
        """, (nombre_usuario, correo, contrasena))

        conexion.commit()
        print("¡Cuenta creada correctamente!")

    except sqlite3.IntegrityError:
        print("Ese nombre de usuario o correo ya está registrado.")

        

def iniciar_sesion_visual():

    # Limpiar la pantalla actual
    for elemento in ventana.winfo_children():
        elemento.destroy()

    # Titulo
    titulo = tk.Label(
        ventana,
        text="INICIAR SESION",
        font=("Arial", 28, "bold"),
        fg="#E63946",
        bg="#151515"
    )
    titulo.pack(pady=30)

    # Nombre de usuario
    tk.Label(
        ventana,
        text="Nombre de usuario",
        fg="white",
        bg="#151515"
    ).pack()

    entrada_usuario = tk.Entry(ventana, font=("Arial", 14))
    entrada_usuario.pack(pady=10)

    # Correo
    tk.Label(
        ventana,
        text="Correo",
        fg="white",
        bg="#151515"
    ).pack()

    entrada_correo = tk.Entry(ventana, font=("Arial", 14))
    entrada_correo.pack(pady=10)

    # Contraseña
    tk.Label(
        ventana,
        text="Contraseña",
        fg="white",
        bg="#151515"
    ).pack()

    entrada_contrasena = tk.Entry(
        ventana,
        font=("Arial", 14),
        show="*"
    )
    entrada_contrasena.pack(pady=10)

    # Funcion para comprobar los datos
    def comprobar_inicio_sesion():

        nombre_usuario = entrada_usuario.get()
        correo = entrada_correo.get()
        contrasena = entrada_contrasena.get()

        # Primero comprobar la base de datos local
        cursor.execute("""
            SELECT id, nombre_usuario
            FROM usuarios
            WHERE nombre_usuario = ?
            AND correo = ?
            AND contrasena = ?
        """, (nombre_usuario, correo, contrasena))

        usuario = cursor.fetchone()

        if usuario is not None:

            print("¡Bienvenido!", usuario[1])
            print("ID del usuario:", usuario[0])

            menu_principal_visual(usuario[0])
            return

        # Si no existe localmente, consultar a la MSI
        resultado = iniciar_cliente(
            nombre_usuario,
            correo,
            contrasena
        )

        if resultado.get("exito"):

            print("¡Bienvenido!", resultado["usuario"])
            print("ID del usuario:", resultado["id"])

            menu_principal_visual(resultado["id"])

        else:

            print("Usuario, correo o contraseña incorrectos.")

def guardar_jugador(jugador, id_usuario):
    cursor.execute("""
        SELECT id FROM jugadores
        WHERE nombre = ? AND apellido = ? AND personaje = ?
        AND usuario_id = ?
    """, (jugador[0], jugador[1], jugador[2], id_usuario))

    existente = cursor.fetchone()

    if existente is not None:
        print("Este personaje ya existe en la base de datos.")
        print("Se utilizara el registro existente.")
        return existente[0]

    cursor.execute("""
        INSERT INTO jugadores(
            nombre, apellido, personaje, vida,
            ataque, defensa, velocidad,
            bebio_caguama, vida_maxima, usuario_id
        )
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (
        jugador[0],
        jugador[1],
        jugador[2],
        jugador[3][0],
        jugador[3][1],
        jugador[3][2],
        jugador[3][3],
        int(jugador[4]),
        jugador[5],
        id_usuario
    ))

    conexion.commit()
    id_jugador = cursor.lastrowid
    print("¡Jugador guardado en la base de datos!")
    return id_jugador




def actualizar_jugador(jugador, id_jugador, id_usuario):
    cursor.execute("""
        UPDATE jugadores
        SET vida = ?,
            ataque = ?,
            defensa = ?,
            velocidad = ?,
            bebio_caguama = ?,
            vida_maxima = ?
        WHERE id = ? AND usuario_id = ?
    """, (
        jugador[3][0],
        jugador[3][1],
        jugador[3][2],
        jugador[3][3],
        int(jugador[4]),
        jugador[5],
        id_jugador,
        id_usuario
    ))

    conexion.commit()

    if cursor.rowcount > 0:
        print("¡Personaje actualizado en la base de datos!")
    else:
        print("No se actualizo: el personaje no existe o no te pertenece.")

def mostrar_jugadores_guardados(id_usuario):
    cursor.execute("""
        SELECT * FROM jugadores
        WHERE usuario_id = ?
    """, (id_usuario,))

    jugadores = cursor.fetchall()

    print("\n--- TUS PERSONAJES GUARDADOS ---")

    if not jugadores:
        print("No tienes personajes guardados todavía.")
        return

    for jugador in jugadores:
        print(jugador)





def cargar_jugador(id_jugador, id_usuario):
    cursor.execute("""
        SELECT * FROM jugadores
        WHERE id = ? AND usuario_id = ?
    """, (id_jugador, id_usuario))

    datos = cursor.fetchone()#obtiene una fila de la tabla jugadores

    if datos is None:
        print("No se encontro el personaje o no te pertenece.")
        return None

    jugador = [
        datos[1],#nombre
        datos[2],#apellido
        datos[3],#tipo de personaje
        [datos[4], datos[5], datos[6], datos[7]],#caracteristicas del personaje
        bool(datos[8]),#si tomo la caguama o no
        datos[9]# vida maxima
    ]

    print("Personaje cargado:", jugador[0])
    return jugador





def elegir_personaje():
    print("\n--- ELIGE TU PERSONAJE ---")
    print("1. Alumno egresado")
    print("2. Alumno pelon")
    print("3. Alumno residente")
    print("4. Alumno practicante")

    opcion = input("Elige tu personaje: ")

    if opcion not in ["1", "2", "3", "4"]:
        print("Opcion incorrecta")
        return elegir_personaje()

    if opcion == "1":
        nombre_personaje = "alumno egresado"
    elif opcion == "2":
        nombre_personaje = "alumno pelon"
    elif opcion == "3":
        nombre_personaje = "alumno residente"
    else:
        nombre_personaje = "alumno practicante"

    estadisticas = mostrar_estadisticas(opcion)

    return nombre_personaje, estadisticas



def mostrar_estadisticas(opcion):
    if opcion == "1":
        return [300, 60, 45, 30]
    elif opcion == "2":
        return [600, 30, 35, 15]
    elif opcion == "3":
        return [450, 45, 37, 22]
    elif opcion == "4":
        return [500, 40, 35, 20]

def crear_jugador(nombre_anterior=""):
    nombre = input("escribe tu nombre:")
    apellido = input("escribe tu apellido:")

    

    if nombre == nombre_anterior:
        print("ese nombre ya esta ocupado")
        return crear_jugador(nombre_anterior)
    print("bienvenido", nombre)
    personaje, estadisticas = elegir_personaje()
    print("tu personaje es:", personaje)
    print("tus estadisticas son:", estadisticas)
    
    bebio_caguama = False
    vida_maxima = estadisticas[0]
    estadisticas_originales = estadisticas.copy()

    return [
        nombre,
        apellido,
        personaje,
        estadisticas,
        bebio_caguama,
        vida_maxima,
        estadisticas_originales
    ]




def decidir_regreso(jugador, vida_maxima, regresos):
    print("\n¡", jugador[0], "ha sido derrotado!")
    print("Oportunidades de regresar:", regresos)
    print("\n1. Regresar al combate")
    print("2. Rendirse")
    print("3. Salir y mostrar estadísticas")

    opcion = input("Elige una opción: ")

    if opcion == "1":
        if regresos > 0:
            jugador[3][0] = vida_maxima #recupera su vida
            regresos = regresos - 1
            print("\n¡", jugador[0], "ha regresado con toda su vida!")
            return "regresar", regresos
        else:
            print("Ya no tienes oportunidades de regresar.")
            return decidir_regreso(jugador, vida_maxima, regresos)

    elif opcion == "2":#termina el combate 
        return "rendirse", regresos

    elif opcion == "3":#sale del combate
        return "salir", regresos

    else:
        print("Opción incorrecta.")
        return decidir_regreso(jugador, vida_maxima, regresos)





def iniciar_combate(jugador1, jugador2):
    regresos1 = 2
    regresos2 = 2
    danio_total1 = 0
    danio_total2 = 0

    curaciones1 = 3
    curaciones2 = 3

    vida_maxima1 = jugador1[5]
    vida_maxima2 = jugador2[5]

    jugador1[3][0] = vida_maxima1
    jugador2[3][0] = vida_maxima2

    ganador = None

    print("\n=== COMIENZA EL COMBATE ===")
    print(jugador1[0], jugador1[1], "-", jugador1[2])
    print("VS")
    print(jugador2[0], jugador2[1], "-", jugador2[2])

    while jugador1[3][0] > 0 and jugador2[3][0] > 0:

        # TURNO DEL JUGADOR 1
        print("\n--- TURNO DE", jugador1[0], "---")

        danio, curaciones1 = realizar_turno(
            jugador1, jugador2, curaciones1
        )

        danio_total1 += danio

        
        if jugador2[3][0] <= 0:
            decision, regresos2 = decidir_regreso(
                jugador2, vida_maxima2, regresos2
            )

            if decision == "regresar":
                continue
            elif decision == "rendirse":
                ganador = jugador1
                break
            elif decision == "salir":
                ganador = None
                break


        # TURNO DEL JUGADOR 2
        print("\n--- TURNO DE", jugador2[0], "---")

        danio, curaciones2 = realizar_turno(
            jugador2, jugador1, curaciones2
        )

        danio_total2 += danio

        
        if jugador1[3][0] <= 0:
            decision, regresos1 = decidir_regreso(
                jugador1, vida_maxima1, regresos1
            )

            if decision == "regresar":
                continue
            elif decision == "rendirse":
                ganador = jugador2
                break
            elif decision == "salir":
                ganador = None
                break


    
    # RESULTADOS DEL COMBATE
    print("\n=== FIN DEL COMBATE ===")

    if ganador is not None:
        print("¡", ganador[0], ganador[1], "HA GANADO!")
    else:
        print("Combate terminado sin ganador.")


    print("\n=== ESTADÍSTICAS FINALES ===")

    print("\nJugador 1:", jugador1[0])
    print("Vida restante:", jugador1[3][0])
    print("Características:", jugador1[3])
    print("Oportunidades de regresar restantes:", regresos1)
    print("Curaciones restantes:", curaciones1)
    print("Daño total causado:", danio_total1)

    print("\nJugador 2:", jugador2[0])
    print("Vida restante:", jugador2[3][0])
    print("Características:", jugador2[3])
    print("Oportunidades de regresar restantes:", regresos2)
    print("Curaciones restantes:", curaciones2)
    print("Daño total causado:", danio_total2)




def elegir_ataque(atacante):
    print("\n--- ATAQUES ---")
    print("1 escupitajo de fuego")
    print("2 patada")
    print("3 cachetada")
    print("4 balazo ala mollera")

    vida_actual = atacante[3][0] #la vida que tiene en ese momento
    vida_maxima = atacante [5] #la vida maxima de ese personaje

    ataque = input("elige tu ataque:")

    if ataque == "1":
        return 50
    elif ataque == "2":
        return 80
    elif ataque  == "3":
        return 120
    elif ataque == "4":
        if vida_actual <= vida_maxima * 0.30 and atacante[4] == True:
            print("¡BALAZO A LA MOLLERA!")
            return 100
        else:
            print("No puedes usar este ataque.")
            print("Necesitas tener 30% de vida o menos y haber tomado una caguama.")
            return elegir_ataque(atacante)

    else:
        print("opcion incorrecta")
        return elegir_ataque(atacante)

    
def atacar(atacante, defensor):
    danio = elegir_ataque(atacante)#daño es igual al ataque que escogio

    defensor[3][0] = max (0, defensor[3][0] - danio) #2 entra a caracteristicas y 0 es la vida del personaje

    print(atacante[0], "causo", danio, "de daño")
    print("vida restante de ", defensor[0], defensor[1], ":", defensor[3][0])

    return danio#devuelve el daño realizado



def elegir_accion():
    print("\n--- QUE QUIERES HACER? ---")
    print("1. Atacar")
    print("2. Curarse")
    
    opcion = input("Elige una opcion: ")

    if opcion == "1" or opcion == "2":
        return opcion
    else:
        print("Opcion incorrecta")
        return elegir_accion()


def realizar_turno(atacante, defensor, curaciones_restantes):
    while True:
        accion = elegir_accion()

        if accion == "1":
            danio = atacar(atacante, defensor) #aqui guarda el daño que hizo el atacante al defensor
            return danio, curaciones_restantes

        elif accion == "2":
            if curaciones_restantes > 0:
                uso = menu_curaciones(atacante)#muestra el menu de curaciones al atacante por que es su turno

                if uso:
                    curaciones_restantes -= 1
                    print("Curaciones restantes:", curaciones_restantes)
                    return 0, curaciones_restantes
            else:
                print("Ya no tienes curaciones disponibles.")







def menu_curaciones(jugador):
    print("\n--- MENU DE CURACIONES ---")
    print("1. Coca Cola Light")
    print("2. Tamal de mole")
    print("3. Chilaquiles verdes")
    print("4. Caguama")
    print("5. Paracetamol")
    print("6. Regresar")

    opcion = input("Elige un consumible: ")

    if opcion == "1":
        jugador[3][0] = min(
            jugador[5],
            jugador[3][0] + 10
        )

        jugador[3][1] = int(jugador[3][1] * 0.95)#conserva solo el 95% total de sus caracteristicas por que se le resto 5%
        jugador[3][2] = int(jugador[3][2] * 0.95)
        jugador[3][3] = int(jugador[3][3] * 0.95)

        print("Usaste Coca Cola Light")
        print("Vida actual:", jugador[3][0])
        print("Estadisticas:", jugador[3])
        return True#indica que sí se utilizó Coca Cola Light y se descuenta una curación

    
    elif opcion == "2":
        jugador[3][0] = min(
            jugador[5],
            jugador[3][0] + int(jugador[5] * 0.10)#suma 10% de vida
        )

        jugador[3][3] = int(jugador[3][3] * 0.90)#deja el 90% de velocidad ya que se diminuyo un 10%

        print("Usaste tamal de mole")
        print("Vida actual:", jugador[3][0])
        print("Estadisticas:", jugador[3])
        return True

    
    elif opcion == "3":
        jugador[3][0] = min(
            jugador[5],
            jugador[3][0] + int(jugador[5] * 0.50)#recupera un 50% de la vida
        )

        jugador[3][1] = int(jugador[3][1] * 1.05)#aumenta un 5% prociento en las caracteristicas
        jugador[3][2] = int(jugador[3][2] * 1.05)
        jugador[3][3] = int(jugador[3][3] * 1.05)

        print("Usaste chilaquiles verdes")
        print("Vida actual:", jugador[3][0])
        print("Estadisticas:", jugador[3])
        return True

    
    elif opcion == "4":
        jugador[3][0] = min(#evita que supere el maximo de vida
            jugador[5],
            jugador[3][0] + int(jugador[5] * 0.15) #calcula el 15% de la vida maxima
        )

        jugador[3][3] = int(jugador[3][3] * 0.50)#reduce la velocidad ala mitad
        jugador[4] = True

        print("Usaste caguama")
        print("Vida actual:", jugador[3][0])
        print("Velocidad reducida a la mitad")
        print("¡Ahora puedes desbloquear el balazo a la mollera!")
        return True

    
    elif opcion == "5":
        jugador[3][0] = jugador[5]
        jugador[3][1] = int(jugador[3][1] * 0.99)#reduce sus caracteristicas un 1%
        jugador[3][2] = int(jugador[3][2] * 0.99)
        jugador[3][3] = int(jugador[3][3] * 0.99)

        print("Usaste paracetamol")
        print("Vida actual:", jugador[3][0])
        print("Estadisticas:", jugador[3])
        return True





    elif opcion == "6":
        print("Regresando...")
        return False

    else:
        print("Opcion incorrecta")
        return False







def menu_principal(id_usuario):
    while True:
        print("\n=== MENU PRINCIPAL ===")
        print("1. Crear personaje")
        print("2. Ataque")
        print("3. Curar")
        print("4. Mostrar informacion")
        print("5. ver jugadores guardados")
        print("6. cargar personajes guardados")
        print("7. actualizar personaje en la base de datos")
        print("8. salir")

        opcion = input("Elige una opcion: ")

        if opcion == "1":
            jugador = crear_jugador()#crea el personaje y obtiene sus datos
            id_personaje_cargado = guardar_jugador(jugador, id_usuario)#cuando creas un personaje, también guardamos su ID en la variable id_personaje_cargado. Después podremos usar ese número para actualizar sus estadísticas tras el combate
            jugador = cargar_jugador(id_personaje_cargado, id_usuario)   

        
        elif opcion == "2":
            if "jugador" in locals():
                print("\n--- ACCESO DEL SEGUNDO JUGADOR ---")

                id_usuario2 = acceso_segundo_usuario()#llama ala funcion que le pide al segundo jugador iniciar sesion
#guarda el id de esa cuenta
                if id_usuario2 is None:
                    continue
                print("\n--- CREAR PERSONAJE DEL SEGUNDO JUGADOR ---")
                jugador2 = crear_jugador(jugador[0])
                id_jugador2 = guardar_jugador(jugador2, id_usuario2)

                iniciar_combate(jugador, jugador2)

                if "id_personaje_cargado" in locals():#si el id del personaje cargado existe
                    actualizar_jugador(jugador, id_personaje_cargado, id_usuario)

                actualizar_jugador(jugador2, id_jugador2, id_usuario2)#actualiza los datos del segundo jugador en la base de datos después del combate

            else:
                print("Primero debes crear tu personaje.")
 

        elif opcion == "3":
            if "jugador" in locals():
                menu_curaciones(jugador)
            else:
                print("primero debes crear tu personaje")
            print("Curar")

        elif opcion == "4":
            if "jugador" in locals():
                print("\n--- INFORMACION DEL PERSONAJE ---")
                print("Nombre:", jugador[0])
                print("Apellido:", jugador[1])
                print("Personaje:", jugador[2])
                print("Vida:", jugador[3][0])
                print("Ataque:", jugador[3][1])
                print("Defensa:", jugador[3][2])
                print("Velocidad:", jugador[3][3])
            else:
                print("Primero debes crear un personaje.")

        elif opcion == "5":
            mostrar_jugadores_guardados(id_usuario)
        
        elif opcion == "6":
            mostrar_jugadores_guardados(id_usuario)

            id_jugador = int(input("Escribe el ID del personaje que quieres cargar: "))

            jugador_cargado = cargar_jugador(id_jugador, id_usuario)

            if jugador_cargado is not None:
                jugador = jugador_cargado
                id_personaje_cargado = id_jugador


        
        
        elif opcion == "7":
            if "id_personaje_cargado" in locals():
                actualizar_jugador(jugador, id_personaje_cargado, id_usuario)
            else:
                print("Primero debes cargar un personaje guardado.")


        elif opcion == "8":
            print("Saliendo del videojuego...")
            break


        else:
            print("Opcion incorrecta, intenta de nuevo.")

            

def acceso_usuarios():
    while True:
        print("\n=== ACCESO AL VIDEOJUEGO ===")
        print("1. Iniciar sesion")
        print("2. Registrar usuario")
        print("3. Salir")

        opcion = input("Elige una opcion: ")

        if opcion == "1":
            id_usuario = iniciar_sesion()

            if id_usuario is not None:
                return id_usuario

        elif opcion == "2":
            registrar_usuario()

        elif opcion == "3":
            print("Saliendo del videojuego...")
            return None

        else:
            print("Opcion incorrecta.")


def acceso_segundo_usuario():
    while True:
        print("\n=== ACCESO DEL SEGUNDO JUGADOR ===")
        print("1. Iniciar sesion")
        print("2. Registrar usuario")

        opcion = input("Elige una opcion: ")

        if opcion == "1":
            id_usuario = iniciar_sesion()

            if id_usuario is not None:
                return id_usuario

        elif opcion == "2":
            registrar_usuario()

        elif opcion == "3":
            print("regresando al menu principal...")
            return None

        else:
            print("Opcion incorrecta.")



#id_usuario = acceso_usuarios()
#print("ID DEL USUARIO QUE INICIO SESION:", id_usuario)

#if id_usuario is not None:
 #   menu_principal(id_usuario)

ventana = tk.Tk()
ventana.title("videojuego de combate")
ventana.geometry("1000x650")
ventana.configure(bg="#151515")
ventana.resizable(False, False)

def iniciar_sesion_visual():

    # Limpiar la pantalla actual
    for elemento in ventana.winfo_children():
        elemento.destroy()

    titulo = tk.Label(
        ventana,
        text="INICIAR SESION",
        font=("Arial", 28, "bold"),
        fg="#E63946",
        bg="#151515"
    )
    titulo.pack(pady=30)

    tk.Label(
        ventana,
        text="Nombre de usuario",
        fg="white",
        bg="#151515"
    ).pack()

    entrada_usuario = tk.Entry(ventana, font=("Arial", 14))
    entrada_usuario.pack(pady=10)

    tk.Label(
        ventana,
        text="Correo",
        fg="white",
        bg="#151515"
    ).pack()

    entrada_correo = tk.Entry(ventana, font=("Arial", 14))
    entrada_correo.pack(pady=10)

    tk.Label(
        ventana,
        text="Contraseña",
        fg="white",
        bg="#151515"
    ).pack()

    entrada_contrasena = tk.Entry(
        ventana,
        font=("Arial", 14),
        show="*"
    )
    entrada_contrasena.pack(pady=10)

    def comprobar_inicio_sesion():

        nombre_usuario = entrada_usuario.get()
        correo = entrada_correo.get()
        contrasena = entrada_contrasena.get()

        cursor.execute("""
            SELECT id, nombre_usuario
            FROM usuarios
            WHERE nombre_usuario = ? AND correo = ? AND contrasena = ?
        """, (nombre_usuario, correo, contrasena))

        usuario = cursor.fetchone()

        if usuario is not None:
            print("¡Bienvenido!", usuario[1])
            print("ID del usuario:", usuario[0])

            menu_principal_visual(usuario[0])

        else:
            print("Usuario, correo o contraseña incorrectos.")

    boton_entrar = tk.Button(
        ventana,
        text="ENTRAR",
        font=("Arial", 16, "bold"),
        bg="#E63946",
        fg="white",
        width=20,
        command=comprobar_inicio_sesion
    )
    boton_entrar.pack(pady=20)

def crear_personaje_visual(id_usuario):

    # Limpiar la pantalla actual
    for elemento in ventana.winfo_children():
        elemento.destroy()

    # Titulo
    titulo = tk.Label(
        ventana,
        text="CREAR PERSONAJE",
        font=("Arial", 28, "bold"),
        fg="#E63946",
        bg="#151515"
    )
    titulo.pack(pady=40)


        # Nombre del jugador
    etiqueta_nombre = tk.Label(
        ventana,
        text="Escribe tu nombre:",
        font=("Arial", 14),
        fg="white",
        bg="#151515"
    )
    etiqueta_nombre.pack()

    entrada_nombre = tk.Entry(ventana, font=("Arial", 14))
    entrada_nombre.pack(pady=5)

    # Apellido del jugador
    etiqueta_apellido = tk.Label(
        ventana,
        text="Escribe tu apellido:",
        font=("Arial", 14),
        fg="white",
        bg="#151515"
    )
    etiqueta_apellido.pack()

    entrada_apellido = tk.Entry(ventana, font=("Arial", 14))
    entrada_apellido.pack(pady=5)

    # Opciones de personajes
    boton_egresado = tk.Button(
        ventana,
        text="ALUMNO EGRESADO",
        font=("Arial", 16, "bold"),
        bg="#333333",
        fg="white",
        width=25,
        height=2,
        command=lambda: seleccionar_personaje_visual(
    "1", id_usuario, entrada_nombre.get(), entrada_apellido.get()
)
    )
    boton_egresado.pack(pady=10)

    boton_pelon = tk.Button(
        ventana,
        text="ALUMNO PELON",
        font=("Arial", 16, "bold"),
        bg="#333333",
        fg="white",
        width=25,
        height=2,
        command=lambda: seleccionar_personaje_visual(
    "2", id_usuario, entrada_nombre.get(), entrada_apellido.get()
)
    )
    boton_pelon.pack(pady=10)

    boton_residente = tk.Button(
        ventana,
        text="ALUMNO RESIDENTE",
        font=("Arial", 16, "bold"),
        bg="#333333",
        fg="white",
        width=25,
        height=2,
        command=lambda: seleccionar_personaje_visual(
    "3", id_usuario, entrada_nombre.get(), entrada_apellido.get()
)
    )
    boton_residente.pack(pady=10)

    boton_practicante = tk.Button(
        ventana,
        text="ALUMNO PRACTICANTE",
        font=("Arial", 16, "bold"),
        bg="#333333",
        fg="white",
        width=25,
        height=2,
        command=lambda: seleccionar_personaje_visual(
    "4", id_usuario, entrada_nombre.get(), entrada_apellido.get()
)
    )
    boton_practicante.pack(pady=10)

def seleccionar_personaje_visual(opcion, id_usuario, nombre, apellido):

    if nombre == "" or apellido == "":
        print("Debes escribir tu nombre y apellido.")
        return

    if opcion == "1":
        nombre_personaje = "alumno egresado"
    elif opcion == "2":
        nombre_personaje = "alumno pelon"
    elif opcion == "3":
        nombre_personaje = "alumno residente"
    else:
        nombre_personaje = "alumno practicante"

    estadisticas = mostrar_estadisticas(opcion)

    jugador = [
        nombre,
        apellido,
        nombre_personaje,
        estadisticas,
        False,
        estadisticas[0]
    ]

    id_personaje = guardar_jugador(jugador, id_usuario)

    print("Personaje seleccionado:", nombre_personaje)
    print("Estadisticas:", estadisticas)
    print("ID del personaje:", id_personaje)
    menu_principal_visual(id_usuario)

    
def menu_principal_visual(id_usuario):

    # Limpiar la pantalla actual
    for elemento in ventana.winfo_children():
        elemento.destroy()

    # Titulo
    titulo = tk.Label(
        ventana,
        text="MENU PRINCIPAL",
        font=("Arial", 28, "bold"),
        fg="#E63946",
        bg="#151515"
    )
    titulo.pack(pady=40)

    # Bienvenida
    bienvenida = tk.Label(
        ventana,
        text="¡Bienvenido al videojuego!",
        font=("Arial", 18),
        fg="white",
        bg="#151515"
    )
    bienvenida.pack(pady=10)

    boton_crear = tk.Button(
        ventana,
        text="CREAR PERSONAJE",
        font=("Arial", 16, "bold"),
        bg="#E63946",
        fg="white",
        width=25,
        height=2,
        command=lambda: crear_personaje_visual(id_usuario)
    )
    boton_crear.pack(pady=15)

    boton_online = tk.Button(
        ventana,
        text="JUGAR ONLINE",
        font=("Arial", 16, "bold"),
        bg="#333333",
        fg="white",
        width=25,
        height=2,
        command=lambda: seleccionar_modo_online(id_usuario)
    )
    boton_online.pack(pady=15)
    




def iniciar_servidor():

    global partida_activa
    global jugador_conectado

    HOST = "0.0.0.0"
    PUERTO = 5000

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    servidor.bind((HOST, PUERTO))
    servidor.listen(5)

    print("Servidor iniciado correctamente.")
    print("Esperando jugadores...")

    while True:

        conexion_jugador, direccion = servidor.accept()

        print("Jugador conectado desde:", direccion)

        try:

            datos_recibidos = conexion_jugador.recv(4096)

            if not datos_recibidos:
                print("El cliente cerro la conexion.")
                continue

            datos = json.loads(datos_recibidos.decode("utf-8"))

            tipo = datos.get("tipo")

            # COMPATIBILIDAD CON EL LOGIN ACTUAL
            if tipo is None and all(
                campo in datos
                for campo in ["usuario", "correo", "contrasena"]
            ):
                tipo = "login"

            # INICIO DE SESION
            if tipo == "login":

                if not all(
                    campo in datos
                    for campo in ["usuario", "correo", "contrasena"]
                ):
                    respuesta = {
                        "exito": False,
                        "mensaje": "Faltan datos para iniciar sesion."
                    }

                else:

                    conexion_bd = sqlite3.connect(
                        r"C:\Users\silia\Downloads\videojuegos.db"
                    )

                    cursor_bd = conexion_bd.cursor()

                    cursor_bd.execute("""
                        SELECT id, nombre_usuario
                        FROM usuarios
                        WHERE nombre_usuario = ?
                        AND correo = ?
                        AND contrasena = ?
                    """, (
                        datos["usuario"],
                        datos["correo"],
                        datos["contrasena"]
                    ))

                    usuario = cursor_bd.fetchone()
                    conexion_bd.close()

                    if usuario is not None:
                        respuesta = {
                            "exito": True,
                            "id": usuario[0],
                            "usuario": usuario[1]
                        }
                    else:
                        respuesta = {
                            "exito": False
                        }

            # GUARDAR PERSONAJE
            elif tipo == "guardar_personaje":

                jugador = datos["jugador"]
                id_usuario = datos["id_usuario"]

                conexion_bd = sqlite3.connect(
                    r"C:\Users\silia\Downloads\videojuegos.db"
                )

                cursor_bd = conexion_bd.cursor()

                cursor_bd.execute("""
                    INSERT INTO jugadores(
                        nombre, apellido, personaje, vida,
                        ataque, defensa, velocidad,
                        bebio_caguama, vida_maxima, usuario_id
                    )
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                """, (
                    jugador["nombre"],
                    jugador["apellido"],
                    jugador["personaje"],
                    jugador["vida"],
                    jugador["ataque"],
                    jugador["defensa"],
                    jugador["velocidad"],
                    int(jugador["bebio_caguama"]),
                    jugador["vida_maxima"],
                    id_usuario
                ))

                conexion_bd.commit()

                id_personaje = cursor_bd.lastrowid

                conexion_bd.close()

                respuesta = {
                    "exito": True,
                    "id_personaje": id_personaje
                }

                print("¡Personaje guardado en la base de datos central!")
                print("Personaje:", jugador["personaje"])

            # UNIRSE A UNA PARTIDA
            elif tipo == "unirse_partida":

                if partida_activa:

                    jugador_conectado = datos["jugador"]

                    respuesta = {
                        "exito": True,
                        "mensaje": "Te has unido a la partida."
                    }

                    print("¡Segundo jugador conectado!")
                    print("Jugador:", jugador_conectado["nombre"])

                else:

                    respuesta = {
                        "exito": False,
                        "mensaje": "No hay ninguna partida disponible."
                    }

            # SOLICITUD DESCONOCIDA
            else:

                respuesta = {
                    "exito": False,
                    "mensaje": "Solicitud no reconocida o incompleta."
                }

            conexion_jugador.sendall(
                json.dumps(respuesta).encode("utf-8")
            )

        except Exception as error:

            print("Error al procesar solicitud:", error)

            try:
                respuesta = {
                    "exito": False,
                    "mensaje": str(error)
                }

                conexion_jugador.sendall(
                    json.dumps(respuesta).encode("utf-8")
                )

            except:
                pass

        finally:
            conexion_jugador.close()




def crear_partida_online():

    global partida_activa
    global jugador_conectado

    partida_activa = True
    jugador_conectado = None

    print("Partida creada correctamente.")
    print("Esperando a que Arthur se una...")

    threading.Thread(
        target=iniciar_servidor,
        daemon=True
    ).start()
        
def iniciar_cliente(nombre_usuario, correo, contrasena):

    HOST = "100.100.147.32"
    PUERTO = 5000

    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:

        cliente.connect((HOST, PUERTO))

        datos = {
            "usuario": nombre_usuario,
            "correo": correo,
            "contrasena": contrasena
        }

        cliente.sendall(
            json.dumps(datos).encode("utf-8")
        )

        respuesta = cliente.recv(4096).decode("utf-8")

        resultado = json.loads(respuesta)

        return resultado

    except Exception as error:

        print("Error de conexión:", error)

        return {"exito": False}

    finally:

        cliente.close()

def seleccionar_modo_online(id_usuario):

    for elemento in ventana.winfo_children():
        elemento.destroy()

    titulo = tk.Label(
        ventana,
        text="VIDEOJUEGO ONLINE",
        font=("Arial", 28, "bold"),
        fg="#E63946",
        bg="#151515"
    )

    titulo.pack(pady=40)

    boton_servidor = tk.Button(
        ventana,
        text="CREAR PARTIDA (SERVIDOR)",
        font=("Arial", 16, "bold"),
        width=25,
        height=2,
        command=crear_partida_online
    )

    boton_servidor.pack(pady=15)

    boton_cliente = tk.Button(
        ventana,
        text="UNIRSE A PARTIDA (CLIENTE)",
        font=("Arial", 16, "bold"),
        width=25,
        height=2,
        command=lambda: iniciar_cliente("", "", "")
    )

    boton_cliente.pack(pady=15)


titulo = tk.Label(ventana, text="Arena de combate", font=("Arial", 32, "bold"), fg="#E63946", bg="#151515")
titulo.pack(pady=50)

boton_iniciar = tk.Button(
    ventana,
    text="INICIAR SESION",
    font=("Arial", 16, "bold"),
    bg="#E63946",
    fg="white",
    width=20,
    height=2,
    command=iniciar_sesion_visual
)

boton_iniciar.pack(pady=15)


boton_registrar = tk.Button(
    ventana,
    text="REGISTRAR USUARIO",
    font=("Arial", 16, "bold"),
    bg="#333333",
    fg="white",
    width=20,
    height=2
)

boton_registrar.pack(pady=15)


boton_salir = tk.Button(
    ventana,
    text="SALIR",
    font=("Arial", 14, "bold"),
    bg="#222222",
    fg="white",
    width=15
)

boton_salir.pack(pady=15)



ventana.mainloop()
