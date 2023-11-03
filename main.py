import cv2
import numpy as np 
import math
import screeninfo
import os
import figuras
import threading
import queue
from cv2 import aruco
import mediapipe as mp
import speech_recognition as sr
if os.path.exists('camara.py'):
    import camara
else:
    print("Es necesario realizar la calibración de la cámara")
    exit()

# Estructura del programa
#                                   Principio
#      Planetas             Estrellas           Satélites                   Representación
# Planeta1...PlanetaN   Estrella1...EstrellaN   Satélite1...SatéliteN

# Forma que tiene el sistema de saber cuál es su situación actual (por si no enfoca bien el marcador, y debe volver a captarlo)
situacion = "principio"
planeta = ""
estrella = ""
satelite = ""

# Para comunicarse entre hilo principal e hilo de escucha
cola_resultados = queue.Queue()

# Para poder hacer la animación de los satélites en caso de Marte y la Tierra
objeto_angulo = 0

# Variables para interpretar el movimiento de los dedos captados por cámara
mp_hands = mp.solutions.hands
factor_escala = 1.0
indice_anterior = (0.0,0.0)
pulgar_anterior = (0.0,0.0)


# ---------------------------------------- TRATAMIENTO DE IMÁGENES ---------------------------------------------------------------
# Función para hacer la detección de la imagen con el que se inicia la aplicación. Se ejecuta siempre, para tener como sistema de referencia
# al centro de la imagen en tiempo real, no unas coordenadas que quedan fijas por pantalla
def detectaImagen(frame):
    # La imagen que va a iniciar la aplicación
    imagen_objetivo = cv2.imread('imgs/miMarcador.png')

    # La hago más pequeña, pues en otro caso hay que acercar mucho la imagen. Antes redimensiono la imagen a captar
    nuevo_ancho = int(imagen_objetivo.shape[1] * 0.5)
    nuevo_alto = int(imagen_objetivo.shape[0] * 0.5)
    imagen_objetivo = cv2.resize(imagen_objetivo, (nuevo_ancho, nuevo_alto))

    # Realizar la detección de la imagen objetivo en el frame actual
    resultado = cv2.matchTemplate(frame, imagen_objetivo, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(resultado)

    # Establecer un umbral de confianza para considerar la detección
    umbral_confianza = 0.2

    if max_val >= umbral_confianza:
        # Se ha comprobado que el contorno detectado es la imagen buscada. Se devuelven las coordenadas al centro
        # Calcular el centro de la detección  EL CENTRO ES APROXIMADO, pues la entrada suele ser imprecisa
        centro_x = max_loc[0] + (imagen_objetivo.shape[1] // 2)
        centro_y = max_loc[1] + (imagen_objetivo.shape[0] // 2)

        return True, centro_x, centro_y
    else:
        return False, -1, -1


# Con esta función lo que vamos a hacer es detectar el movimiento de los dedos en dos posibles casos:
#       - Si el pulgar e índice se separan, se hace zoom (escalamos a mayor factor de escala), y si se juntan, se quita zoom (se escala a menor factor de escala)
#       - Si el corazón esta solo, y este se mueve, la imagen se mueve hacia donde se mueva el dedo

def procesarMano(frame):
    global factor_escala, pulgar_anterior, indice_anterior
    # Indico que voy a usar detección de manos, especificando a la librería mediapipe
    with mp_hands.Hands(
    static_image_mode=True,
    max_num_hands=1,
    min_detection_confidence=0.5) as hands:
        # Proceso todo lo relativo a la imagen y detección, la biblioteca va a trabajar con la matriz RGB del frame captado
        image = cv2.flip(frame,1)
        image_rgb = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
        heigth, width, _ = image.shape
        # Obtener un array con los puntos de interés de la mano captada. Solo vamos a usar dos: la punta del pulgar y la punta del índice
        results = hands.process(image_rgb)

        if results.multi_hand_landmarks:
        # Voy a obtener los puntos claves de la mano y después quedarme con el pulgar e índice
            for hand_landmarks in results.multi_hand_landmarks:
                pulgar = (hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x*width,hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y*heigth)
                indice = (hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].x*width,hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y*heigth)
              
                dist_anterior = math.sqrt((indice_anterior[0] - pulgar_anterior[0])**2 + (indice_anterior[1] - pulgar_anterior[1])**2)
                dist_ahora = math.sqrt((indice[0] - pulgar[0])**2 + (indice[1] - pulgar[1])**2)
           
                if dist_ahora > dist_anterior:
                    factor_escala += 0.1
                    if factor_escala > 1.4:
                        factor_escala = 1.4
                if dist_ahora < dist_anterior:
                    factor_escala -= 0.1
                    if factor_escala < 0.5:
                        factor_escala = 0.5

            # Actualizar las variables de referencia
                pulgar_anterior = pulgar
                indice_anterior = indice



# --------------------------------PROCESAMIENTO DE LENGUAJE: THREADING -------------------------------------------------

# Comprueba si el usuario ha dicho algo, y en ese caso devuelve la palabra dicha
def obtenerEscuchaDeProceso():
    global cola_resultados
    if not cola_resultados.empty():
        return cola_resultados.get()
    else:
        return "Nada"


# Reconocer si el usuario dice alguna palabra (reconocimiento de lenguaje natural)
def reconoceHabla():
    global cola_resultados
    global situacion            # Para acabar el programa, se hará por detección de voz
    reconoce = sr.Recognizer()

    with sr.Microphone() as source:
        while True:
            try:
                audio = reconoce.listen(source)
                texto = reconoce.recognize_google(audio, language='es-ES')
                print(texto)
                cola_resultados.put(texto)  # Pone en la cola compartida la palabra captada
                if texto == "terminar":
                    situacion = "terminar"
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print("Error al realizar la solicitud:", e)
                break

            # Para acabar el bucle. Debe acabar con el hilo que ejecuta la aplicación
            if situacion=="terminar":
                break
    

# -------------------------------------------------------------------------------------------------------------------------------

# ------------------------------------------- REALIDAD AUMENTADA ---------------------------------------------------------------
# Mostrar la pantalla de inicio de la aplicación y procesar le RA y lo que diga el usuario

# Devolver la ruta a la textura

def obtenerTexturaCuerpo():
    global planeta, estrella, satelite

    if(planeta=="tierra"):
        return "imgs/tierra.jpg"
    if(planeta == "Venus"):
        return "imgs/venus.jpg"
    if(planeta == "Urano"):
        return "imgs/urano.jpg"
    if(planeta == "Saturno"):
        return "imgs/saturno.jpg"
    if(planeta == "Neptuno"):
        return "imgs/neptuno.jpg"
    if(planeta == "mercurio"):
        return "imgs/mercurio.jpg"
    if(planeta == "Marte"):
        return "imgs/marte.jpg"
    if(planeta == "Júpiter"):
        return "imgs/jupiter.jpg"
    if(estrella == "sol"):
        return "imgs/sol.png"
    if(satelite == "luna"):
        return "imgs/luna.jpg"
    if(satelite == "Deimos"):
        return "imgs/deimos.png"
    if(satelite == "Fobos"):
        return "imgs/fobos.jpg"
    if(satelite == "Plutón"):       # Por no excluir al pobre :)
        return "imgs/pluton.jpg"
    
# Es imposible que los tamaños sean proporcionales a la realidad (el Sol es muy grande, lo que hace que, por ejemplo, la Tierra, se vea minúscula)
# Aunque no sean proporciones reales, se procurará respetar la relación 'es más pequeño que', pero no para los satélites, para que puedan ser vistos
def obtenerRadioCuerpo():
    global planeta, estrella, satelite
    if(planeta=="tierra"):
        return 100
    if(planeta == "Venus"):
        return 100
    if(planeta == "Urano"):
        return 120
    if(planeta == "Saturno"):
        return 160
    if(planeta == "Neptuno"):
        return 140
    if(planeta == "mercurio"):
        return 100
    if(planeta == "Marte"):
        return 110
    if(planeta == "Júpiter"):
        return 170
    if(estrella == "sol"):
        return 190
    if(satelite == "luna"):
        return 100
    if(satelite == "Deimos"):
        return 100
    if(satelite == "Fobos"):
        return 100
    if(satelite == "Plutón"):       # Por no excluir al pobre :)
        return 100

# De cada cuerpo, se mostrará nombre, masa (kg), radio real (km), velocidad rotación, velocidad traslación
def obtenerInformacionCuerpo():
    global planeta, estrella, satelite

    if(planeta == "tierra"):
        return ["Tierra", "Masa: 5.972*10^24 kg", "Radio: 6371 km", "Velocidad de rotacion: 465.11 m/s", "Velocidad de traslacion: 30000 m/s"]
    if(planeta == "Venus"):
        return ["Venus","Masa: 4.875*10^24 kg","Radio: 6051.8 km","Velocidad de rotacion: 6.52 km/h","Velocidad de traslacion: 26.108 km/h"]
    if(planeta == "Urano"):
        return ["Urano","Masa: 8.681*10^25 kg","Radio: 25.362 km","Velocidad de rotacion: 14.794 km/h","Velocidad de traslacion: 24.516 km/h"]
    if(planeta == "Saturno"):
        return ["Saturno","Masa: 5.683*10^26 kg","Radio: 58.232 km","Velocidad de rotacion: 36.840 km/h","Velocidad de traslacion: 34.705 km/h"]
    if(planeta == "Neptuno"):
        return ["Neptuno","Masa: 1.024*10^26 kg","Radio: 24.622 km","Velocidad de rotacion: 9.719 km/h","Velocidad de traslacion: 19.548 km/h"]
    if(planeta == "mercurio"):
        return ["Mercurio","Masa: 3.285*10^23 kg","Radio: 2439.7 km","Velocidad de rotacion: 10.83 km/h","Velocidad de traslacion: 172.404 km/h"]
    if(planeta == "Marte"):
        return ["Marte","Masa: 6.39*10^23 kg","Radio: 3389.5 km","Velocidad de rotacion: 866 km/h","Velocidad de traslacion: 86.868 km/h"]
    if(planeta == "Júpiter"):
        return ["Jupiter","Masa: 1.898*10^27 kg","Radio: 69911 km","Velocidad de rotacion: 45583 km/h","Velocidad de traslacion: 47016 km/h"]
    if(estrella == "sol"):
        return ["Sol","Masa: 1.989*10^30 kg","Radio: 695508 km","Velocidad de rotacion: 1,997 km/s","Velocidad de traslacion (centro de la galaxia): 828000 km/h"]
    if(satelite == "luna"):
        return ["Luna","Masa: 7.349*10^22 kg","Radio: 1740 km","Velocidad de rotacion: -","Velocidad de traslacion: 3873.6 km/h"]
    if(satelite == "Deimos"):
        return ["Deimos","Masa: 2.244*10^15 kg","Radio: 6.2 km","Velocidad de rotacion: -","Velocidad de traslacion: 4864.8 km/h"]
    if(satelite == "Fobos"):
        return ["Fobos","Masa: 1.072*10^16 kg","Radio: 11,267 km","Velocidad de rotacion: -","Velocidad de traslacion: 7696.7 km/h"]
    if(satelite == "Plutón"):       
        return ["Pluton","Masa: 1,30*1022 kg","Radio: 1188.3 km","Velocidad de rotacion: -","Velocidad de traslacion: 4.74 km/s"]


# Mostrar el menú principal de la aplicación, donde podemos derivarnos a Planetas, Estrellas o Satélites
def gestionarPrincipio(coordX,coordY,frame):
    global situacion, factor_escala    # Común al resto de funciones. Determina la funcionalidad el programa

    # Generación del rectángulo y lo que se va a ver
    nuevoFrame = figuras.obtenerGrid(coordX,coordY-150,3,frame,["Planetas","Estrellas","Satelites"],factor_escala) # Que no salga de la pantalla
    frame = nuevoFrame

    # Reconocimiento de voz, si procede, para cambiar a otro menú
    palabra = obtenerEscuchaDeProceso()     # Funciona bien la cola compartida

    if palabra=="planetas" or palabra=="planeta":
        situacion = "planetas"
    if palabra=="estrellas" or palabra=="estrella":
        situacion = "estrellas"
    if palabra=="satélites" or palabra =="satélite":
        situacion = "satélites"
    if palabra == "animación":
        situacion = "animación"
    if palabra == "terminar":
        situacion = "terminar"

    return frame
    

# Función general para representar cualquier cuerpo (planeta, estrella o satélite)
# FALTA PONER LOS RADIOS A ESCALA MUY REDUCIDA Y EN PROPORCIÓN--->REFERENCIA: EL SOL (POR SER EL MÁS GRANDE). SI NO, USAR JÚPITER COMO REFERENCIA
# ANIMACIÓN DE LOS SATÉLITES DE MARTE Y LA TIERRA. Seguir parametrización ((r+p)cos(t)+coordX,(r+p)sen(t)+coordY), donde p>0 ya lo ajustaré cuando vea necesario
def gestionarCuerpo(coordX,coordY,frame):
    # Primero: Obtener el modelo de qué cuerpo queremos animar. Si planeta="", estrellas="", entonces satelite!="", jugar con esto
    # Segundo: Tras obtener el modelo, dibujar el grid y el modelo al lado suyo. Usar el frame pasado por argumento
    # Hacer captura del movimiento (girar cuerpo celeste o hacer zoom)
    # Tercero: Escuchar a ver si dice 'Atrás', para hacer planeta=""
    # Cuarto: Devolver frame
    global planeta, estrella, satelite, objeto_angulo, factor_escala
    palabra = obtenerEscuchaDeProceso()
    textura = obtenerTexturaCuerpo()
    radio = obtenerRadioCuerpo()
    informacion = obtenerInformacionCuerpo()
   
    frame1, objeto_angulo = figuras.dibujarCuerpo(round(coordX-250),round(coordY+100),round(factor_escala*radio),frame,textura,informacion,planeta,objeto_angulo,factor_escala)

    if palabra == "atrás":
        planeta = ""
        estrella=""
        satelite=""
        
    return frame1
    


def gestionarPlanetas(coordX,coordY,frame):
    global situacion    # Se declaran como globales porque son comunes a todas las funciones y determinan el funcionamiento del programa
    global planeta, factor_escala

    nuevoFrame = frame
    if planeta != "":           # Se ha seleccionado un planeta para ver la información
        nuevoFrame = gestionarCuerpo(coordX,coordY,frame)   # Aquí se superpondrá al frame lo que tenga que ver con UN cuerpo celeste
    else:   # Se recrea el menú de los planetas (misma manera que menú principal). Se supone número fijo de planetas
        numPlanetas = 8
        nuevoFrame = figuras.obtenerGrid(coordX,coordY-200,numPlanetas,frame,["Mercurio","Venus","Tierra","Marte","Jupiter","Saturno","Urano","Neptuno"],factor_escala)
        frame = nuevoFrame

        # Reconocer si quiere algún planeta o volver atrás
        palabra = obtenerEscuchaDeProceso()
        # Si son nombres propios, los devuelve con primera letra en mayúscula. Si no, como 'tierra' o 'mercurio', los da en minúscula
        if palabra=="atrás":                
            situacion = "principio"
        if palabra == "mercurio":
            planeta = "mercurio"
        if palabra == "Venus":
            planeta = "Venus"
        if palabra == "tierra":
            planeta = "tierra"
        if palabra == "Marte":
            planeta = "Marte"
        if palabra == "Júpiter":
            planeta = "Júpiter"
        if palabra == "Saturno":
            planeta = "Saturno"
        if palabra == "Urano":
            planeta = "Urano"
        if palabra == "Neptuno":
            planeta = "Neptuno"
        if palabra == "Plutón":
            planeta = "Plutón"
        if palabra == "terminar":
            situacion = "terminar"

    return nuevoFrame

def gestionarEstrellas(coordX,coordY,frame):
    global situacion    # Se declaran como globales porque son comunes a todas las funciones y determinan el funcionamiento del programa
    global estrella, factor_escala

    nuevoFrame = frame
    if estrella != "":           # Se ha seleccionado un planeta para ver la información
        nuevoFrame = gestionarCuerpo(coordX,coordY,frame)   # Aquí se superpondrá al frame lo que tenga que ver con UN cuerpo celeste
    else:   # Se recrea el menú de los planetas (misma manera que menú principal). Se supone número fijo de planetas
        numEstrellas = 1
        nuevoFrame = figuras.obtenerGrid(coordX,coordY-200,numEstrellas,frame,["Sol"],factor_escala)
        frame = nuevoFrame

        # Reconocer si quiere algún planeta o volver atrás
        palabra = obtenerEscuchaDeProceso()
        # Si son nombres propios, los devuelve con primera letra en mayúscula. Si no, como 'tierra' o 'mercurio', los da en minúscula
        if palabra=="atrás":                
            situacion = "principio"
        if palabra == "sol":
            estrella = "sol"
        if palabra == "terminar":
            situacion = "terminar"

    return nuevoFrame

def gestionarSatelites(coordX,coordY,frame):
    global situacion    # Se declaran como globales porque son comunes a todas las funciones y determinan el funcionamiento del programa
    global satelite,factor_escala

    nuevoFrame = frame
    if satelite != "":           # Se ha seleccionado un planeta para ver la información
        nuevoFrame = gestionarCuerpo(coordX,coordY,frame)   # Aquí se superpondrá al frame lo que tenga que ver con UN cuerpo celeste
    else:   # Se recrea el menú de los planetas (misma manera que menú principal). Se supone número fijo de planetas
        numSatelites = 3
        nuevoFrame = figuras.obtenerGrid(coordX,coordY-200,numSatelites,frame,["Luna","Deimos","Fobos"],factor_escala)
        frame = nuevoFrame

        # Reconocer si quiere algún planeta o volver atrás
        palabra = obtenerEscuchaDeProceso()
        # Si son nombres propios, los devuelve con primera letra en mayúscula. Si no, como 'tierra' o 'mercurio', los da en minúscula
        if palabra=="atrás":                
            situacion = "principio"
        if palabra == "luna":
            satelite = "luna"
        if palabra == "Deimos":
            satelite = "Deimos"
        if palabra[-2:] == "os":    # El micrófono no capta bien la palabra 'Fobos', pero las que capta acaban en 'os'
            satelite = "Fobos"
        if palabra == "terminar":
            situacion = "terminar"

    return nuevoFrame

# -------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------- GESTIÓN DE LA APLICACIÓN --------------------------------------------------------
# Para representar los modelos de realidad aumentada. Si se tapa el marcador, el usuario debe volver a ver qué estaba viendo
def procesaAplicacion(coordX,coordY,frame):
   # datos_bola = figuras.crearBolaUnidad(coordX,coordY)
   # x, y, r, color = datos_bola
    # Poner en el frame captado la figura
   # espacio = cv2.imread('imgs/espacio.jpg',0)

    # Primero vemos si se ha detectado movimiento con las manos
    miFrame = frame
    procesarMano(frame)

    if situacion=="principio":
        miFrame = gestionarPrincipio(coordX,coordY,frame)
    if situacion=="planetas":
        miFrame = gestionarPlanetas(coordX,coordY,frame)
    if situacion=="estrellas":
        miFrame = gestionarEstrellas(coordX,coordY,frame)
    if situacion=="satélites":
        miFrame = gestionarSatelites(coordX,coordY,frame)

    return miFrame

def buclePrincipal():
    global situacion

    # Primero obtengo información de la pantalla (pues quiero que el tamaño sea de toda la pantalla, en función de qué ordenador y/o móvil ejecute)

    screen = screeninfo.get_monitors()[0]
    screen_width = screen.width
    screen_height = screen.height

    # Inicio la webcam

    cap = cv2.VideoCapture(0)

    cv2.namedWindow('PracticaCUIA', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('PracticaCUIA', screen_width, screen_height)

    # En caso de ver el marcador, la aplicación solo se detendrá si el usuario lo quiere, diciendo 'Salir'
    exito = False

    # Bucle de la aplicación
    while True:
        ret, frame = cap.read()

        if not ret:
            print("No he podido leer el frame")
            break
        
        datos_marcador = detectaImagen(frame)
        # Este condicional intenta manejar si ha habido algún error en la función que capta el marcador
        if datos_marcador is not None:
            exito, coordX, coordY = datos_marcador  # Coordenadas del centro del marcador
            if exito:
                miFrame = procesaAplicacion(coordX,coordY,frame)  # Trabajo con el centro de la imagen, y dibujamos en el frame, que luego se mostrará
                cv2.imshow('PracticaCUIA', miFrame)
            else:
                cv2.imshow('PracticaCUIA', frame)
        else:
            cv2.imshow('PracticaCUIA', frame)

        cv2.waitKey(1)      # Necesario para mostrar el frame
        if situacion == "terminar":      # Finalizar el bucle. Debe acabar con el otro hilo. De esta manera, se busca que intenten acabar a la vez
            break

    cap.release()
    cv2.destroyAllWindows()
# ------------------------------------------------------------------------------------------------------------------------------------



# Función main
if __name__ == '__main__':
    # Creación de dos hilos: uno para el programa principal y otro para la escucha
    hilo_escucha = threading.Thread(target=reconoceHabla)
    hilo_aumento = threading.Thread(target=buclePrincipal)

    # Lanzar ambos hilos
    hilo_aumento.start()
    hilo_escucha.start()

    # Hacer una especio de join para acabar el programa. La manera de acabar el programa es pulsando el espacio, ' ' (ambos bucles)
    hilo_escucha.join()
    hilo_aumento.join()