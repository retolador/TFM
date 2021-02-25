#Autor Pau Salas Cerda
#Data 25 de febrer de 2021
#Llibreries necessàries
import pandas as pd
from pandas import DataFrame
import numpy as numpy
from haversine import haversine, Unit
from statsmodels.tsa.api import ExponentialSmoothing, SimpleExpSmoothing, Holt
import numpy as np
from sklearn.linear_model import LogisticRegression
import json
import time
from multiprocessing import Pool
import multiprocessing as mp
from multiprocessing import Process, Pipe, current_process
import psycopg2
from psycopg2 import Error


class Classificacio_mobilitat(object):
    """
    Classe per classificar els diferents tipus de transport dels diferents individus
    """
    def __init__(self, dataframe, aps_informacio , llistat_usuaris, processos):
        """
        Constructor
        """
        self.dataframe = dataframe
        #super(, self).__init__()
        self.aps_informacio = aps_informacio
        self.llistat_usuaris = llistat_usuaris
        self.processos = processos


        self.periode_deadline = 332 #Limit en segons per diferenciar els subgrups

        self.velocitat_maxima = 60 #Límit per considerar-se velocitat aberrant

        self.probabilitat_minima = 0.4 #Probabilitat mínima per poder crear el model

        self.dia = self.llistat_usuaris['dia'].iloc[1]
        # self.dia = self.dia.replace("/","_") # Al tenir en diferent format, però es va cambiar i està tot correcte

        self.subgrup = list() #Contingut de totes les dades del usuari

        #self.hora_inici_subgrup = list() # Per indicar quin temps inicia el subgrup

        self.resultat_model = list() #Per crear el model de predicció
        self.array_model = list()    #Per poder crear el model de predicció

        self.array_dades = list() #Se li afegeixen les dades per obtenir els resultats
        self.array_resultat_final = list()

        self.usuaris_mobils = list() # llistat dels usuaris únics mòbils

        self.param_dic = {
        "dbname"      : "smartwifi",
        "user"  : "postgres",
        "host"      : "localhost",
        "password"  : "passf0rd"
        }
    def get_llista_usuaris_mobil(self):
        """
        Obtenir la llista dels usuaris mòbils
        """

        usuaris_mobils = self.llistat_usuaris[self.llistat_usuaris['class_mob_est'] == "mobil"]

        usuaris_mobils = usuaris_mobils['clientmac']

        self.usuaris_mobils = usuaris_mobils

    def eliminar_velocitats_aberrants(self, vector):
        """
        Eliminació de velocitats aberrants
        """
        subgrups_velocitats = list()
        longitud_usuaris = len(self.usuaris_mobils)
        limit_inferior = int(longitud_usuaris*vector/self.processos)
        limit_superior = int(longitud_usuaris/self.processos+longitud_usuaris*vector/self.processos)
        usuaris_mobils = self.usuaris_mobils[(limit_inferior):(limit_superior)]

        #Per fer la intersecció entre els punts al mateix temps
        for i in usuaris_mobils:
            entrades_dispositiu = self.dataframe[i == self.dataframe["clientmac"]]
            entrades_dispositiu = entrades_dispositiu.sort_values(by=['seentime'])
            entrades_dispositiu = entrades_dispositiu.reset_index(drop=True)

            longitud = len(entrades_dispositiu)-1

            for indice_fila in range(longitud):



                try: #Casos en el que hi ha dues entrades al mateix temps
                    if entrades_dispositiu.loc[indice_fila,'seentime'] == entrades_dispositiu.loc[indice_fila + 1,'seentime']:
                        entrades_dispositiu.loc[indice_fila,'lat'] = (entrades_dispositiu.loc[indice_fila,'lat'] + entrades_dispositiu.loc[indice_fila + 1,'lat'])/2
                        entrades_dispositiu.loc[indice_fila,'lng'] = (entrades_dispositiu.loc[indice_fila,'lng'] + entrades_dispositiu.loc[indice_fila + 1,'lng'])/2
                        entrades_dispositiu = entrades_dispositiu.drop(entrades_dispositiu.index[indice_fila+1])
                except:
                    pass


            entrades_dispositiu = entrades_dispositiu.reset_index(drop=True) #Posa nous índeos als elements
            longitud = len(entrades_dispositiu)-1

            #Reiteració per les velocitats que superen un umbral
            for indice_fila in range(longitud):

                posicio1 = (entrades_dispositiu.loc[indice_fila,'lat'], entrades_dispositiu.loc[indice_fila,'lng'])
                posicio2 = (entrades_dispositiu.loc[indice_fila + 1,'lat'], entrades_dispositiu.loc[indice_fila + 1,'lng'])
                espai = haversine(posicio1, posicio2) # En km
                temps = (entrades_dispositiu.loc[indice_fila + 1,'seentime'] - entrades_dispositiu.loc[indice_fila,'seentime'])/3600 # En hores
                velocitat = espai/temps
                if velocitat > self.velocitat_maxima:
                    try:
                        #velocitat aberrant es farà la mitja amb l'anterior i el següent
                        entrades_dispositiu.loc[indice_fila,'lat'] = (entrades_dispositiu.loc[indice_fila - 1,'lat'] + entrades_dispositiu.loc[indice_fila + 1,'lat'])/2
                        entrades_dispositiu.loc[indice_fila,'lng'] = (entrades_dispositiu.loc[indice_fila - 1,'lng'] + entrades_dispositiu.loc[indice_fila + 1,'lng'])/2
                        entrades_dispositiu.loc[indice_fila,'seentime'] = (entrades_dispositiu.loc[indice_fila - 1,'seentime'] + entrades_dispositiu.loc[indice_fila + 1,'seentime'])/2
                    except:
                        pass

            #Una vegada acabat la segona iteració d'eliminació d'errors és procedeix
            valors = mobilitat.subgrups_velocitat(entrades_dispositiu)
            if len(valors) > 0:
                subgrups_velocitats.append(valors)
        #print(subgrups_velocitats)
        return subgrups_velocitats

    def subgrups_velocitat(self, entrades_dispositiu):
        """
        Divideix el grup de velocitats de l'usuari en diferents subgrups
        """

        entrades_dispositiu = entrades_dispositiu.reset_index(drop=True)
        longitud = len(entrades_dispositiu)-1
        #Inicialitzar els valors.
        subgrups_proces = list()
        subgrup_velocitat = list()
        contador_subgrup = 0

        for indice_fila in range(longitud):
            posicio1 = (entrades_dispositiu.loc[indice_fila,'lat'], entrades_dispositiu.loc[indice_fila,'lng'])
            posicio2 = (entrades_dispositiu.loc[indice_fila + 1,'lat'], entrades_dispositiu.loc[indice_fila + 1,'lng'])
            espai = haversine(posicio1,posicio2)
            temps = (entrades_dispositiu.loc[indice_fila + 1,'seentime'] - entrades_dispositiu.loc[indice_fila,'seentime']) # En hores
            velocitat =(espai*3600)/temps



            if temps < self.periode_deadline and indice_fila != longitud-1:
                subgrup_velocitat.append(velocitat)
                contador_subgrup += 1

            elif contador_subgrup > 3: #Es mira si hi ha valors.

                #Suavitzat simple ExponentialSmoothing
                dades_suavitzades = mobilitat.simple_exponential_smoothing(subgrup_velocitat)


                #Obtenir l'hora d'inici del subgrup

                #Obtenir els diferents APs
                aps = entrades_dispositiu.loc[(indice_fila+1-contador_subgrup) :indice_fila]
                aps = aps.drop_duplicates(subset=['apmac'])
                diferents_aps = len(aps)/len(entrades_dispositiu)

                #Diferents zones que han visitat els ususaris

                arees = pd.merge(aps, self.aps_informacio, left_on='apmac', right_on='mac')
                if len(arees) > 1:
                    arees = arees.drop_duplicates(subset=['zona'])
                    nombre_arees = len(arees)
                else:
                    nombre_arees = 1

                #Obtenir hora inici i final del subgrup per comprendre quin temps tarda
                hora_inici = entrades_dispositiu.loc[indice_fila-contador_subgrup+1,'seentime']
                hora_inici = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(hora_inici))
                hora_final = entrades_dispositiu.loc[indice_fila,'seentime']
                hora_final = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(hora_final))
                subgrup_usuari =( dades_suavitzades, diferents_aps, nombre_arees, hora_inici, hora_final, entrades_dispositiu.loc[indice_fila,'clientmac'])
                #subgrups_proces.append(subgrup_usuari)
                #Inicialitzar el llistat i el contador de subgrup
                #return subgrup_usuari
                subgrups_proces.append(subgrup_usuari)
                subgrup_velocitat = list()
                contador_subgrup = 0
            else:
                subgrup_velocitat = list()
                contador_subgrup = 0
                #print(subgrup_usuari)

        return subgrups_proces



    def processar_subgrups(self, dades_usuaris_mobils):
        """
        Crea els conjunts de dades amb les seves probabilitats
        """
        self.subgrup = dades_usuaris_mobils

        for value in self.subgrup:
            Probabilitat_quiet = 0
            Probabilitat_caminar = 0
            Probabilitat_altres = 0


            for i in range(len(value[0])):
                if i < 2:
                    Probabilitat_quiet += 1/len(value[0])
                if i>3 and i<7:
                    Probabilitat_caminar += 1/len(value[0])
                if i>13 and i<50:
                    Probabilitat_altres += 1/len(value[0])

            if Probabilitat_quiet > self.probabilitat_minima:
                self.resultat_model.append("quiet")
                mobilitat.afegir_valor_array_model(value, Probabilitat_quiet, Probabilitat_caminar, Probabilitat_altres)
            if Probabilitat_caminar > self.probabilitat_minima:
                self.resultat_model.append("caminar")
                mobilitat.afegir_valor_array_model(value, Probabilitat_quiet, Probabilitat_caminar, Probabilitat_altres)
            if Probabilitat_altres > self.probabilitat_minima:
                self.resultat_model.append("altres")
                mobilitat.afegir_valor_array_model(value, Probabilitat_quiet, Probabilitat_caminar, Probabilitat_altres)

            valors = (Probabilitat_quiet, Probabilitat_caminar, Probabilitat_altres, value[1], value[2])
            self.array_dades.append(valors)


    def simple_exponential_smoothing(self,subgrup_velocitat):
        """
        Simple Exponential Smoothing
        """
        fit3 = SimpleExpSmoothing(subgrup_velocitat).fit(smoothing_level=0.6,optimized=False)
        dades_suavitzades = fit3.fittedvalues
        return dades_suavitzades


    def afegir_valor_array_model(self, value, Probabilitat_quiet, Probabilitat_caminar, Probabilitat_altres):
        """
        Per afegir valors al array per crear el model
        """
        valors = (Probabilitat_quiet, Probabilitat_caminar, Probabilitat_altres, value[1], value[2])
        self.array_model.append(valors)

    def create_model(self):
        """
        Crea el model per poder predir els valors
        """
        self.model = LogisticRegression(solver='liblinear', random_state=0).fit(self.array_model,self.resultat_model)

    def get_model(self):
        """
        Retorna el model creat
        """
        return self.model

    def actualitzar_dataframe(self, model):
        """
        Actualitza el dataframe amb les noves dades
        """
        #Predicció de totes les dades
        resultat = model.predict(self.array_dades)
        self.resultat = resultat
        contador_resultat = 0
        #boolean = False


        df_subgrup = pd.DataFrame(self.subgrup, columns =['velocitats', 'diferents aps','zones', 'hora inici','hora final','clientmac'])

        #Creació de dos dataframes diferents. Un dels usuaris i l'altre el de transports.
        for indice_fila, fila in self.llistat_usuaris.iterrows():
            if fila['class_mob_est'] == "mobil":

                data=[]
                subgrup_usuari = df_subgrup[df_subgrup['clientmac'] == fila['clientmac']]

                #if len(subgrup_usuari) > 1:
                  #  boolean = True



                if len(subgrup_usuari) >= 1: #Per conèixer si en té més d'una entrada
                    for indice_filab,filab  in subgrup_usuari.iterrows():
                        #hora_utc = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(filab['hora inici']))
                        item = {"hora inici": filab['hora inici'], "hora final": filab['hora final'], "transport" : resultat[contador_resultat]}
                        contador_resultat += 1
                        data.append(item)


                    jsonData=json.dumps(data) #Es guarda el resultat en csv
                    self.llistat_usuaris.loc[indice_fila, 'transport'] = jsonData
                    #if boolean == True:
                     #   print(jsonData)
                      #  boolean = False
                else: #Casos que tenen poques entrades en els subgrups i no es poden classificar
                    self.llistat_usuaris.loc[indice_fila, 'transport'] = "Entrades insuficients"

            elif fila['class_mob_est'] == "estatic":
                self.llistat_usuaris.loc[indice_fila, 'transport'] = "fixat"
            else:
                self.llistat_usuaris.loc[indice_fila, 'transport'] = "NA"

    def crear_dataframe_transports(self):
        """
        Crea el dataframe dels transports
        """
        llistat_transports = list()
        for variables,resultat in zip(self.subgrup, self.resultat):
            dades = (variables[5] ,resultat, variables[3], variables[4], self.dia)
            llistat_transports.append(dades)
        self.transports_classificacio = pd.DataFrame(llistat_transports, columns = ['clientmac','transport','hora_inici','hora_final','dia'] )
    def guardar_dataframe_transports(self):
        """
        Guarda en format csv la classificació dels transports
        """
        self.transports_classificacio.to_csv('classificacio_transports_{}.csv'.format(self.dia), index = False, header=True)

    def escriure_dataframe(self):
        """
        Per escriure el dataframe en local en format csv
        """
        self.llistat_usuaris.to_csv ('classificacio_usuaris_mobilitat_{}.csv'.format(self.dia), index = False, header=True)

    def get_classificacio_transports(self):
        """
        Retorna la classificacio dels transports
        """
        return self.transports_classificacio
    def connect(self):
        """
        Connect to the PostgreSQL database server
        """
        conn = None
        try:
            # connect to the PostgreSQL server
            print('Connecting to the PostgreSQL database...')
            conn = psycopg2.connect("dbname='smartwifi' user='postgres' host='localhost' password='passf0rd'")
            print("Connected to the PostgreSQL database!!!")
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
           # sys.exit(1)
        return conn


    def single_insert(self, conn, insert_req):
        """
        Execute a single INSERT request
        """
        cursor = conn.cursor()
        try:
            cursor.execute(insert_req)
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            print("Error: %s" % error)
            conn.rollback()
            cursor.close()
            # Per aturar els logs quan hi ha un error
            conn.cloese()
            aaaaaaaa #to stop the logs
            return 1
        cursor.close()

    def get_llistat_usuaris(self):
        """
        Retorna el llistat dels usuaris
        """
        return self.llistat_usuaris

    def get_resultat_resum(self):
        """
        Retorna un petit resum del resultat del algoritme
        """
        longitud_transports = len(self.transports_classificacio)
        quiet = self.transports_classificacio[self.transports_classificacio['transport'] == "quiet"]
        quiet = len(quiet)/longitud_transports
        caminar = self.transports_classificacio[self.transports_classificacio['transport'] == "caminar"]
        caminar = len(caminar)/longitud_transports
        altres = 1 - caminar - quiet
        print("Percentatge d'instancies en estat de quiet: {} \n".format(quiet))
        print("Percentatge d'instancies en estat de caminar: {} \n".format(caminar))
        print("Percentatge d'instancies en estat d'altres: {} \n".format(altres))
# main
if __name__ == "__main__":
    # execute only if run as a script
    #Variables inici main
    starttime = time.time()
    dades_usuaris_mobils = list()

    processos=4
    processos_vector = [0,1,2,3]

    #Booleans per guardar en local els csv resultants
    guardar_llista_usuaris = False
    guardar_llista_transports = False
    mostrar_resum = False

    # dataframe = pd.read_csv('observacionsEstiu20190724mod.csv',sep=';')
    #dataframe = dataframe[:(100000)] #Solament per comprovar el funcionament de l'algoritme


    dataframe = pd.read_csv('observacions_dia.csv',sep=',')
    #dataframe = dataframe[:(40000)] #Solament per comprovar el funcionament de l'algoritme

    aps_informacio = pd.read_csv('distribucioapsampliat.csv',sep=',')
    classificacio_usuaris = pd.read_csv('classificacio_usuaris_primera_part.csv',sep=',')

    #Creació de l'objecte i obtenció dels usuaris mòbils
    mobilitat = Classificacio_mobilitat(dataframe, aps_informacio, classificacio_usuaris, processos)
    mobilitat.get_llista_usuaris_mobil()
    print('Primera part took {} seconds'.format(time.time() - starttime))
   # with Pool(processos) as p:
    #    dades_usuaris_mobils.append(p.map(mobilitat.eliminar_velocitats_aberrants, processos_vector))
    pool = mp.Pool()
    dades_usuaris_mobils = pool.map(mobilitat.eliminar_velocitats_aberrants, processos_vector)
    #print(dades_usuaris_mobils)
    dades_usuaris_mobils = [ent for sublist in dades_usuaris_mobils for ent in sublist]
    dades_usuaris_mobils = [ent for sublist in dades_usuaris_mobils for ent in sublist]
    print('Part multiprocessing took {} seconds'.format(time.time() - starttime))
    mobilitat.processar_subgrups(dades_usuaris_mobils)
    mobilitat.create_model()
    modelo = mobilitat.get_model()
    mobilitat.actualitzar_dataframe(modelo)
    print('Part predicció took {} seconds'.format(time.time() - starttime))



    mobilitat.crear_dataframe_transports()
    if guardar_llista_transports == True:
        mobilitat.guardar_dataframe_transports() #guarda el resultat en un csv a la màquina virtual

    if guardar_llista_usuaris == True:
        mobilitat.escriure_dataframe()

    if mostrar_resum == True:
        mobilitat.get_resultat_resum() #Mostra per consola un resum dels resultats

    #Part per insertar la classificació dels dispositius a la base de dades
    conn = mobilitat.connect()
    dades_usuari = mobilitat.get_llistat_usuaris()
    for index_fila,fila in dades_usuari.iterrows(): #Primer inserta les dades dels dispositius
        query = """
        INSERT into tfmpausalas_classificacio_usuaris(clientmac, dia, class_hab_esp, class_est_mob) values('%s','%s','%s','%s');
        """ % (str(fila['clientmac']),str(fila['dia']),str(fila['class_hab_esp']), str(fila['class_mob_est'])) #str per codificar-ho tot en UTF-8
        mobilitat.single_insert(conn, query)
    #Segona part on inserta la classifiació dels transports
    classificacio_transport = mobilitat.get_classificacio_transports()
    for index_fila,fila in classificacio_transport.iterrows(): #Segon importa les dades dels transports
        query = """
        INSERT into tfmpausalas_classificacio_transports(clientmac, dia, transport, hora_inici, hora_fi ) values('%s','%s','%s','%s','%s');
        """ % (str(fila['clientmac']), str(fila['dia']),str(fila['transport']),str(fila['hora_inici']), str(fila['hora_final']))
        mobilitat.single_insert(conn, query)
    conn.close()
    print('Algoritme sencer took {} seconds'.format(time.time() - starttime))
