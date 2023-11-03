#import pygame
import math
import cv2
import numpy as np
import pyrender
import trimesh


def crearBolaUnidad(coordX,coordY):
    radio = 200
    WHITE = (0, 0, 0)

    datos_bola=(coordX,coordY,radio,WHITE)

    return datos_bola


# Sistema de referencia: marcador. En simulación, coordenadas Sol==coordenadas Marcador
#def crearAstro(coordX,coordY,radio,textura):


def obtenerGrid(coordX,coordY,particion,frame,palabras,factor_escala):
    # Tamaño que va a ocupar la tabla del menú
    MEDIO_GRID = 200.0 * factor_escala
    lado = MEDIO_GRID * 2
    long_div = lado / particion
    mitad_long_div = long_div / 2

    # Extremo superior izquierdo
    extremo_sup_x = int(coordX - mitad_long_div)-20     # Agrandar más a lo largo el menú
    extremo_sup_y = int(coordY - mitad_long_div)

    # Extremo inferior derecho
    extremo_inf_x = int(coordX + mitad_long_div)+20
    extremo_inf_y = int(coordY + mitad_long_div)

    for i in range(particion):
        # Coordenadas del rectángulo de cada partición
        sup_x = extremo_sup_x
        sup_y = int(extremo_sup_y + i * long_div)
        inf_x = extremo_inf_x
        inf_y = int(extremo_sup_y + (i + 1) * long_div)

        # Dibujar el rectángulo de la partición en el frame
        cv2.rectangle(frame, (sup_x, sup_y), (inf_x, inf_y), (255, 0, 0), -1)

        # Tamaño de las letras
        escala = 0.5*factor_escala
        grosor = 1
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Posición del texto
        text_width, text_height = cv2.getTextSize(palabras[i], font, escala*factor_escala, grosor)[0]
        x = int(coordX - text_width / 2)
        y = int(sup_y + long_div / 2 + text_height / 2)

        # Dibujar la palabra en el frame
        cv2.putText(frame, palabras[i], (x, y), font, escala, (0, 0, 0), grosor, cv2.LINE_AA)

    return frame


def dibujarCuerpo(coordX, coordY, radio, frame, textura,informacion,planeta,objeto_angulo,factor_escala):
    # PRIMERO: CREACIÓN DE LA FIGURA QUE LLEVARÁ LA TEXTURA DEL CUERPO CELESTE

     # Cargar la imagen de textura
    textura_imagen = cv2.imread(textura)

    # Crear una imagen en blanco para dibujar la esfera
    esfera = np.zeros((2 * radio, 2 * radio, 3), dtype=np.uint8)

    # Dibujar la esfera como un círculo en la imagen en blanco
    cv2.circle(esfera, (radio, radio), radio, (255, 255, 255), -1)

    # Obtener las coordenadas de la región de interés en el frame
    x1 = max(coordX - radio, 0)
    y1 = max(coordY - radio, 0)
    x2 = min(coordX + radio, frame.shape[1])
    y2 = min(coordY + radio, frame.shape[0])

    # Verificar si la región de interés está completamente fuera de los límites
    if x1 >= frame.shape[1] or x2 <= 0 or y1 >= frame.shape[0] or y2 <= 0:
        return frame, factor_escala

    # Ajustar las coordenadas de recorte para evitar cortes en el lado contrario
    if x1 < 0:
        x2 -= x1
        x1 = 0
    if y1 < 0:
        y2 -= y1
        y1 = 0
    if x2 > frame.shape[1]:
        x1 -= (x2 - frame.shape[1])
        x2 = frame.shape[1]
    if y2 > frame.shape[0]:
        y1 -= (y2 - frame.shape[0])
        y2 = frame.shape[0]

    # Recortar la región de interés del frame, teniendo en cuenta los límites de la imagen
    roi = frame[y1:y2, x1:x2]

    # Redimensionar la imagen de textura al tamaño de la región de interés
    textura_imagen = cv2.resize(textura_imagen, (roi.shape[1], roi.shape[0]))

    # Asegurarse de que la imagen de textura tenga 3 canales
    if textura_imagen.shape[-1] == 1:
        textura_imagen = cv2.cvtColor(textura_imagen, cv2.COLOR_GRAY2BGR)

    # Calcular las coordenadas para copiar la región de interés con la textura aplicada
    x_offset = max(-x1, 0)
    y_offset = max(-y1, 0)
    x_end = x_offset + x2 - x1
    y_end = y_offset + y2 - y1

    # Aplicar la textura a la región de interés de la esfera
    esfera_con_textura = np.where(esfera[y_offset:y_end, x_offset:x_end] != 0, textura_imagen[y_offset:y_end, x_offset:x_end], roi)

    # Copiar la región de interés con la textura aplicada al frame original
    frame_con_esfera = frame.copy()
    frame_con_esfera[y1:y2, x1:x2] = esfera_con_textura

    frame = frame_con_esfera.copy()

    # TERCERO: CREACIÓN DEL RECUADRO CON LA INFORMACIÓN DEL CUERPO CELESTE

    animaX = coordX
    animaY = coordY

    coordX = coordX+350
    coordY = coordY-200
    particion = len(informacion)

    # Tamaño que va a ocupar la tabla del menú
    MEDIO_GRID = 200.0*factor_escala
    lado = MEDIO_GRID * 2
    long_div = lado / particion
    mitad_long_div = long_div / 2

    # Extremo superior izquierdo
    extremo_sup_x = int(coordX - mitad_long_div) - 50     # Agrandar más a lo largo el menú
    extremo_sup_y = int(coordY - mitad_long_div)

    # Extremo inferior derecho
    extremo_inf_x = int(coordX + mitad_long_div) + 50
    #extremo_inf_y = int(coordY + mitad_long_div)

    for i, texto in enumerate(informacion):
        # Coordenadas del rectángulo de cada partición
        sup_x = extremo_sup_x
        sup_y = int(extremo_sup_y + i * long_div)
        inf_x = extremo_inf_x
        inf_y = int(extremo_sup_y + (i + 1) * long_div)

        # Dibujar el rectángulo de la partición en el frame
        cv2.rectangle(frame, (sup_x, sup_y), (inf_x, inf_y), (192, 192, 192), -1)

        # Tamaño de las letras
        escala = 0.3*factor_escala  # Ajustar el valor para reducir el tamaño de la letra
        grosor = 1
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Posición del texto
        text_width, text_height = cv2.getTextSize(texto, font, escala, grosor)[0]
        x = int(coordX - text_width / 2)
        y = int(sup_y + long_div / 2 + text_height / 2)

        # Dibujar el texto en el frame
        cv2.putText(frame, texto, (x, y), font, escala, (0, 0, 0), grosor, cv2.LINE_AA)


     # Cuarta parte: Dibujar el objeto girando alrededor del centro, si es la Tierra o Marte

    radio_satelites_anima = round(20*factor_escala)
    objeto_x = int(animaX + (radio + 70) * np.cos(objeto_angulo))
    objeto_y = int(animaY + (radio + 70) * np.sin(objeto_angulo))

    # Para superponer los satélites, el código va a ser el mismo que antes, por lo que no se documenta. Solo cambian algunos datos
    if planeta == "tierra":
        textura_imagen = cv2.imread("imgs/luna.jpg")
        textura_imagen = cv2.resize(textura_imagen, (2 * radio_satelites_anima, 2 * radio_satelites_anima))

        esfera_anima = np.zeros((2 * radio_satelites_anima, 2 * radio_satelites_anima, 3), dtype=np.uint8)
        cv2.circle(esfera_anima, (radio_satelites_anima, radio_satelites_anima), radio_satelites_anima, (255, 255, 255), -1)

        x1 = max(objeto_x - radio_satelites_anima, 0)
        y1 = max(objeto_y - radio_satelites_anima, 0)
        x2 = min(objeto_x + radio_satelites_anima, frame.shape[1])
        y2 = min(objeto_y + radio_satelites_anima, frame.shape[0])

        if x1 >= frame.shape[1] or y1 >= frame.shape[0] or x2 <= 0 or y2 <= 0:
            return frame, objeto_angulo

        if x1 < 0:
            esfera_anima = esfera_anima[:, -x1:]
            x2 -= x1
            x1 = 0
        if y1 < 0:
            esfera_anima = esfera_anima[-y1:, :]
            y2 -= y1
            y1 = 0
        if x2 > frame.shape[1]:
            x2 = frame.shape[1]
        if y2 > frame.shape[0]:
            y2 = frame.shape[0]

        roi = frame[y1:y2, x1:x2]

        if roi.shape[0] > 0 and roi.shape[1] > 0:
            textura_imagen_resized = cv2.resize(textura_imagen, (roi.shape[1], roi.shape[0]))
            esfera_anima_resized = cv2.resize(esfera_anima, (roi.shape[1], roi.shape[0]))
            esfera_con_textura = np.where(esfera_anima_resized != 0, textura_imagen_resized, roi)

            frame_con_figura = frame.copy()
            frame_con_figura[y1:y2, x1:x2] = esfera_con_textura

            frame = frame_con_figura.copy()

    if planeta == "Marte":
        textura_imagen = cv2.imread("imgs/deimos.png")
        textura_imagen = cv2.resize(textura_imagen, (2 * radio_satelites_anima, 2 * radio_satelites_anima))

        esfera_anima = np.zeros((2 * radio_satelites_anima, 2 * radio_satelites_anima, 3), dtype=np.uint8)
        cv2.circle(esfera_anima, (radio_satelites_anima, radio_satelites_anima), radio_satelites_anima, (255, 255, 255), -1)

        x1 = max(objeto_x - radio_satelites_anima, 0)
        y1 = max(objeto_y - radio_satelites_anima, 0)
        x2 = min(objeto_x + radio_satelites_anima, frame.shape[1])
        y2 = min(objeto_y + radio_satelites_anima, frame.shape[0])

        if x1 >= frame.shape[1] or y1 >= frame.shape[0] or x2 <= 0 or y2 <= 0:
            return frame, objeto_angulo

        if x1 < 0:
            esfera_anima = esfera_anima[:, -x1:]
            x2 -= x1
            x1 = 0
        if y1 < 0:
            esfera_anima = esfera_anima[-y1:, :]
            y2 -= y1
            y1 = 0
        if x2 > frame.shape[1]:
            x2 = frame.shape[1]
        if y2 > frame.shape[0]:
            y2 = frame.shape[0]

        roi = frame[y1:y2, x1:x2]

        if roi.shape[0] > 0 and roi.shape[1] > 0:
            textura_imagen_resized = cv2.resize(textura_imagen, (roi.shape[1], roi.shape[0]))
            esfera_anima_resized = cv2.resize(esfera_anima, (roi.shape[1], roi.shape[0]))
            esfera_con_textura = np.where(esfera_anima_resized != 0, textura_imagen_resized, roi)

            frame_con_figura = frame.copy()
            frame_con_figura[y1:y2, x1:x2] = esfera_con_textura

            frame = frame_con_figura.copy()

        # Especial mención a este satélite. Va a ser simétrico al satélite Deimos
        textura_imagen = cv2.imread("imgs/fobos.jpg")
        radio_satelites_anima+=10   # Simetría respecto centro del planeta
        diffX = objeto_x - animaX
        diffY = objeto_y - animaY
        simX = animaX - diffX
        simY = animaY - diffY
        textura_imagen = cv2.resize(textura_imagen, (2 * radio_satelites_anima, 2 * radio_satelites_anima))

        esfera_anima = np.zeros((2 * radio_satelites_anima, 2 * radio_satelites_anima, 3), dtype=np.uint8)
        cv2.circle(esfera_anima, (radio_satelites_anima, radio_satelites_anima), radio_satelites_anima, (255, 255, 255), -1)

        x1 = max(simX - radio_satelites_anima, 0)
        y1 = max(simY - radio_satelites_anima, 0)
        x2 = min(simX + radio_satelites_anima, frame.shape[1])
        y2 = min(simY + radio_satelites_anima, frame.shape[0])

        if x1 >= frame.shape[1] or y1 >= frame.shape[0] or x2 <= 0 or y2 <= 0:
            return frame, objeto_angulo

        if x1 < 0:
            esfera_anima = esfera_anima[:, -x1:]
            x2 -= x1
            x1 = 0
        if y1 < 0:
            esfera_anima = esfera_anima[-y1:, :]
            y2 -= y1
            y1 = 0
        if x2 > frame.shape[1]:
            x2 = frame.shape[1]
        if y2 > frame.shape[0]:
            y2 = frame.shape[0]

        roi = frame[y1:y2, x1:x2]

        if roi.shape[0] > 0 and roi.shape[1] > 0:
            textura_imagen_resized = cv2.resize(textura_imagen, (roi.shape[1], roi.shape[0]))
            esfera_anima_resized = cv2.resize(esfera_anima, (roi.shape[1], roi.shape[0]))
            esfera_con_textura = np.where(esfera_anima_resized != 0, textura_imagen_resized, roi)

            frame_con_figura = frame.copy()
            frame_con_figura[y1:y2, x1:x2] = esfera_con_textura

            frame = frame_con_figura.copy()

    objeto_angulo += np.radians(1)  # Ajusta la velocidad de rotación


    return frame, objeto_angulo