#se desea crear un videojuego el cual simule el comportamiento de un personaje el cual tendra las siguientes opciones iniciales, crear personaje (nombre del personaje y sera unique, definir un apellido 
#y cuanta vida inicial tendra(de tipo entero), el ataque con un porcentaje de 50 puntos y contara con defensa de 25 puntos y una velocidad de 15 puntos)
#segunda opcion de menu principal llamado ataque y mostrara un menu llamado menu de ataque con 4 ataques iniciales, el primero escupitajo de fuego el cual 
#disminuira 50 puntos de vida, segundo ataque patada fuerte la cual disminuye 80 puntos de vida, tercer ataque es cachetada guajolotera y disminuye 120 puntos de vida y cuarto atque balazo
#a la mollera y disminuye  100 puntos, solo cuando la vida este al 30% y haya tomado una caguama y la ultima opcion regresar que retorna al menu anterior y tercer opcion menu principal es menu "curar" como una tienda, 
#primer opcion "coca cola light" que sube 10 puntos de vida y baja estadisticas un 5%, segunda opcion de curacion es "tamal de mole" aumenta 10% de vida y baja 10% de velocidad
#tercer opcion "chilaquiles verdes" aumenta la mitad de la vida inicial y aumenta 5% todas las estadisticas y por ultimo "caguama" aumenta 15% de vida y disminuye la velocidad a la mitad
#y por ultimo "paracetamos " aumenta 100% de vida y disminuye 1% todas las estadisticas y opcion "regresar" y siguiente opcion mostrar toda la info de personaje como nombres y estadisticas. 
#personaje con:
#100%vida:5corazones
#75-99%: 4 corazones
#50-74%: 3 corzones
#25-54%dos corazones
#1-25%:1 corazon
#1=25%
#0=personaje morido
#caguama no se puede tomar si no has comido nada o si lo haces te diga se te va a subir rapido
#si tienes 100% de vida ya no excede el porcentaje aunque comas mas
#revivir:---> 




class Videojuego:
    #metodo contructor
    def __init__(self,nombre,apellido, vida, ataque, defensa,velocidad):
        self.nombre=nombre
        self.apellido=apellido
        self.vida=vida
        self.ataque=50
        self.defensa=25
        self.velocidad=15
#metodos del personaje que podra usar
    def crear(self):
        nombre_in=input("Ingrese el nombre del personaje:").lower()
        apellido_in=input("Ingrese el apellido del personaje:").lower()
        #try:#terminar para que no se meta otra cosa que no sea entero
        vida_in=int(input("Ingrese la vida inicial de su personaje ❤️:"))
        #vidamx=vida_in#aqui se guarda la vida con que se creo el personaje
        self.nombre=nombre_in
        self.apellido=apellido_in
        self.vida=vida_in

        print(f"EL PERSONAJE: {self.nombre}{self.apellido}")
        print(f"Vida:{self.vida} \nAtaque: {self.ataque}\n Defensa:{self.defensa}\nVelocidad{self.velocidad}")
        print(f"SE CREO CON EXITO 🧌")

    def curar(self):
        print("[1]==COCA COLA LIGHTH🥤")
        print("[2]==TAMAL MOLE🫔")
        print("[3]==CHILAQUILES ROJOS🍴")
        print("[4]==CAGUAMA🍺")
        print("[5]==PARACETAMOL💊")
        print("[6]==REGRESAR🚪")
        op_curar=input("Seleccione una opcion de la tiendita: ")

        if op_curar=="1":
            self.vida=self.vida+10

            percent_at=self(50*0.05)
            self.ataque=self.ataque-percent_at

            percent_def=self(25*0.05)
            self.defensa=self.defensa-percent_def

            percent_velo=self(15*0.05)
            self.velocidad=self.velocidad-percent_velo

        if op_curar=="2":
            self.vida=self.curar+20

            percent_velo=self(15*0.10)
            self.velocidad=self.velocidad-percent_velo

        if op_curar=="3":
            self.vida=self.curar+self.vida*2
            #si tengo el 100% de vida y tomo cocacola que me da 5% de vida ya no puede sobrepasar el 100% de vida solo baja el rendimiento, checar eso en todos

        if op_curar=="4":
            self.vida=self.curar+15

            percent_velo=self(15*0.10)
            self.velocidad=self.velocidad-percent_velo




            

        
    def atacar(self):
        pass
    def mostrar(self):
        print(f"EL PERSONAJE: {self.nombre}{self.apellido}")
        print(f"Vida:{self.vida} \nAtaque: {self.ataque}\n Defensa:{self.defensa}\nVelocidad{self.velocidad}")

    def menu(self):
        while True:
            print("\n==MENU==")
            print("[1]==CREAR PERSONAJE")
            print("[2]==ATACAR")
            print("[3]==CURAR")
            print("[4]==MOSTRAR")
            print("[5]==CERRAR")
            op=str(input("SELECCIONAR UNA ACCION:🧌"))
            if op=="1":
                self.crear()
            elif op=="2":
                self.atacar()
            elif op=="3":
                self.curar()
            elif op=="4":
                self.mostrar()
            elif op=="5":
                print("GRACIAS POR JUGAR!!!🕹️")
                break

            if self.vida==0:
                while True:
                    print("[1]==REVIVIR")
                    print("[2]==MOSTRAR")
                    print("[3]==RENDIRSE")
                    op_d=input("SELECCIONE UNA OPCION: ")

personaje1=Videojuego("","",0,50,25,15)
personaje1.menu()