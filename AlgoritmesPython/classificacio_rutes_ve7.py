#Autor Pau Salas Cerda
#Data 25 de febrer de 2021
#Llibreries necessàries
import psycopg2
from psycopg2 import Error
#import Classificaciodispositius as cldis
import pandas as pd
#import arules as ar
from pandas import DataFrame
#from arules.utils import five_quantile_based_bins, top_bottom_10, top_5_variant_variables
import numpy as np
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from multiprocessing import Pool
import multiprocessing as mp
from multiprocessing import Process, Pipe, current_process
import time
import psutil




class Classificacio_rutes(object):
    """
    Classe per obtenir les regles d'associació entre zones
    """
    def __init__(self, dataframe, llista_usuaris, aps_informacio, processos, temps_string, franja, dia_setmana):
        """
        Constructor
        """
        self.dataframe = dataframe
        self.llista_usuaris = llista_usuaris
        self.aps_informacio = aps_informacio
        self.processos = processos
        self.items = list()

        self.dia = temps_string

        self.dia_setmana = dia_setmana

        self.franja = franja # Franja de temps demati, horabaixa o vespre seleccionat

        # O se recull des propi CSV creat o

        self.llistat_aps_individual = list()
        self.llistat_aps_zona = list()

        self.inici_feina_laboral = time.strptime("8:00", "%H:%M")
        self.inici_entreteniment_laboral = time.strptime("17:00", "%H:%M")
        self.inici_entreteniment_festiu = time.strptime("10:00", "%H:%M")

         #self.param_dic = {
        #"host"      : "-",
        #"database"  : "-",
        #"user"      : "-",
        #"password"  : "-"}



    def set_dataframe_horaris(self):
        """
        Situa el dataframe en una regió de temps demati, horabaixa o vespre segons el dia que es
        """
        self.dataframe = self.dataframe.sort_values(by=['seentime'])
        self.dataframe = self.dataframe.reset_index()

        if self.dia_setmana == "Saturday" or self.dia_setmana == "Sunday":
            festiu_limit = rutes.limit_cap_setmana()
            for i in festiu_limit:
                feina_limit = i
                descans_limit = i

        elif self.franja == "descans":
            descans_limit = rutes.limit_superior_feina()
            for i in descans_limit:
                descans_limit = i

        elif self.franja == "feina":
            descans_limit = rutes.limit_superior_feina()
            for i in descans_limit:
                descans_limit = i

            feina_limit = rutes.limit_inferior_feina()
            for i in feina_limit:
                feina_limit = i

        elif self.franja == "entreteniment":
            feina_limit = rutes.limit_inferior_feina()
            for i in feina_limit:
                feina_limit = i

        if self.franja == "descans":
            self.dataframe = self.dataframe[0:descans_limit]
        elif self.franja == "feina":
            self.dataframe = self.dataframe[descans_limit:feina_limit]
        elif self.franja == "entreteniment":
            self.dataframe = self.dataframe[feina_limit:(len(self.dataframe)-1)]

    def limit_superior_feina(self):
        """
        Obté el límit de la franja descnas i feina
        """
        for index_fila, fila in self.dataframe.iterrows():
            if time.gmtime(fila['seentime']).tm_hour == self.inici_feina_laboral.tm_hour:
                yield index_fila
                break

    def limit_inferior_feina(self):
        """
        Obté el límit de la franja feina i entreteniment
        """
        for index_fila, fila in self.dataframe.iterrows():
            if time.gmtime(fila['seentime']).tm_hour == self.inici_entreteniment_laboral.tm_hour:
                yield index_fila
                break
    def limit_cap_setmana(self):
        """
        Obté el límit dels cap de setmnaes
        """
        for index_fila, fila in self.dataframe.iterrows():
            if time.gmtime(fila['seentime']).tm_hour == self.inici_entreteniment_festiu.tm_hour:
                yield index_fila
                break

    def merge_taules(self):
        """
        Per fusionar les taules en una sola, per poder classificar els dispositius en zones
        """
        self.merge_dades = pd.merge(self.dataframe, self.aps_informacio, left_on='apmac', right_on='mac')


    def get_merge_taules(self):
        """
        Retorna la taula combinada
        """
        return self.merge_dades
    def set_items_list(self):
        """
        Crea el llistat d'items
        """
        self.items = self.aps_informacio.drop_duplicates(subset=['zona_name'])
        self.items = self.items['zona_name']
        #print(self.items)

    def eliminate_dataframe_inicial(self):
        """
        Elimina dades que ja no serveixen per deixar espai a la memòria
        """
        del self.dataframe

    def eliminate_dataframe_merge(self):
        """
        Elimina el dataframe merge per lliberar espai de memòria
        """
        del self.merge_dades

    def aps_llistat_zona(self, vector):
        """
        Per obtenir el llistat de les zones
        """

        llistat_aps_zona = list()

        #Dividir la base de dades en diferents processos per acelerar el temps d'execució
        longitud_usuaris = len(self.llista_usuaris)
        limit_inferior = int(longitud_usuaris*vector/self.processos)
        limit_superior = int(longitud_usuaris/self.processos+longitud_usuaris*vector/self.processos)
        dades_usuaris = self.llista_usuaris[(limit_inferior):(limit_superior)]



        llistat_aps_zona_yield = rutes.get_llistat_zones_usuari(dades_usuaris)
        for i in llistat_aps_zona_yield:
            llistat_aps_zona.append(i)

        print("Classificacio de zones realitzat")
        return llistat_aps_zona

    def get_llistat_zones_usuari(self, dades_usuaris):
        """
        Retorna els llistats de zones dels usuaris a partir d'un boc de dades
        """
        for indice_fila, fila  in dades_usuaris.iterrows():

            if fila['class_mob_est'] == "mobil":
                entrades_dispositiu = self.merge_dades[fila['clientmac'] == self.merge_dades["clientmac"]]
                entrades_dispositiu = entrades_dispositiu.drop_duplicates(subset=['zona'])
                if len(entrades_dispositiu) > 1:
                    llista_aps = entrades_dispositiu['zona_name']
                    yield llista_aps




    def set_dataframe(self, taula_de_dades):
        """
        Transforma el dataframe al de tipus 1 i zeros necessari per poder executar l'algoritme
        """


        te = TransactionEncoder()
        te_ary = te.fit(taula_de_dades).transform(taula_de_dades) #El transforma a un de True i False
        self.ohe_df = pd.DataFrame(te_ary, columns=te.columns_)

        print("Transformació del dataframe al de 1 i zeros realitzat")


    def get_ohe_df(self):
        """
        Retorna el dataframe transformat al de uns i zeros
        """
        return self.ohe_df

    def set_freq_items(self):
        """
        Crear set dels items per  zones
        """
        support = input("Inscriu el suport mínim entre 0 i 1")
        starttime = time.time()
        support = float(support)
        try:
            self.freq_items = apriori(rutes.get_ohe_df(), min_support=support, use_colnames=True, verbose=1)
        except:
            print("Input error")
        print("Creació freq items: {}".format(time.time()-starttime))

    def get_freq_items(self):
        """
        Obtenir l'item set freqüent
        """
        return self.freq_items


    # Function to convert
    def listToString(self,llista):
        """
        funció per transformar una llista en un String per poder-lo pujar a la base de dades
        """

        # initialize an empty string
        str1 = " "

        # return string
        return (str1.join(llista))

    def set_rules(self):
        """
        Per mostrar els items sets freqüents a través de lift o la confiança
        """
        tipus = input("Argument per visualitzar les regles lift o confidence:")
        minim = input("Threshold que ha de superar")
        starttime = time.time()

        try:
            minim = float(minim)
            self.rules = association_rules(rutes.get_freq_items(), metric=tipus, min_threshold= minim)
            #Afegeix dues noves columnes amb informació
            self.rules["antecedent_len"] = self.rules["antecedents"].apply(lambda x: len(x))
            self.rules["consequent_len"] = self.rules["consequents"].apply(lambda x: len(x))
            #Eliminar elements redundants a la base de dades
            self.rules = self.rules[ (self.rules['consequent_len'] == 1) ]
            #Els consequents estiran en format unicode, però els antecedents seran frozensets
            self.rules["antecedents"] = [list(x) for x in self.rules["antecedents"]]
            self.rules["consequents"] =  self.rules["consequents"].apply(lambda x: list(x)[0]).astype("unicode")
            print(self.rules.head())
        except AttributeError:
            print("No hi ha freq_items")
        except:
            print("Input Error")
        print("Creació de les regles: {}".format(time.time()-starttime))
    def print_rules(self):
        """
        Imprimació de les regles a partir d'uns paràmetres de l'usuari
        """
        try:
            print("-------------Visualitzador de les regles:----------- ")
            print("Indiqui paràmetre númeric:")
            print("    -lift ")
            print("    -confidence ")
            print("    -leverage ")
            print("    -conviction ")
            print("O indiqui paràmetre de zona ")
            print("    -antecedents ")
            print("    -consequents")
            parametre = input("Paràmetre per visualitzar les regles:  ")
            startime = time.time()
            rules = self.rules
        except:
           print("No hi ha regles escrites")

        try:
            #Casos de zona
            if parametre == "consequents" or parametre == "antecedents":
                nom_zona = input("Indicar la zona per visualitzar:  ")
                subconjunt = rutes.crear_subconjunt(parametre, rules, nom_zona)
                print(subconjunt)

            #Casos númerics
            else:
                rules = rules.sort_values(ascending=False, by = [parametre])
                print(rules.head())
        except Exception as error:
            print(error)

        print("Creació freq items: {}".format(time.time()-starttime))

    def crear_subconjunt(self, parametre, rules, nom_zona):
        """
        Crea un subconjunt d'una zona a partir d'un conjunt de regles
        """

        #for index,fila in
        nous_rules = list()
        for index_fila, fila in rules.iterrows():
            if nom_zona in rules[parametre]:
                nous_rules.append(fila)

        nous_rules = pd.DataFrame(data=nous_rules)
        return nous_rules

    def get_rules(self):
        """
        Per obtenir el set de regles
        """
        return self.rules

    def download_csv_result(self):
        """
        Descarrega una copia en csv del resultat obtingut
        """
        Nom_dataframe = input("Introdueix un nóm per guardar el csv:   ")
        try:
            self.rules['franja_horaria'] = self.franja
            self.rules.to_csv('{}.csv'.format(Nom_dataframe), index = False, header=True)
        except Exception as error:
            print(error)

    def transformacio_sql(self):
        """
        transforma les dades al del tipus SQL perque no hi hagi problemes de pujada
        """

        for  indice_fila ,fila in self.rules.iterrows():
            # Per transformar l'apostrof en doble per poder-lo implmentar a la base de dades
            a_string = rutes.listToString(fila['antecedents'])
            a_string = a_string.replace("'", "''")
            a_string = a_string.replace(";", "~")
            a_string = a_string.replace("&", "yy")
            self.rules.loc[indice_fila, "antecedents"] = a_string

            b_string = fila['consequents']
            b_string = b_string.replace("'", "''")
            b_string = b_string.replace(";", "~")
            b_string = b_string.replace("&", "yy")
            self.rules.loc[indice_fila, "consequents"] = b_string

            c_string = fila['conviction'] #Casos per el que sorgeix infinit
            if c_string == float("inf"):
                self.rules.loc[indice_fila, "conviction"] = -1


    def switch_menu(self, argument):
        """
        Per realitzar les diferents opcions
        """
        if argument  == "1":

            # Obté un subconjunt d'itemsets freqüents
            rutes.set_freq_items()


        elif argument == "2":
            # A partir d'un subconjunt d'itemsets freqüents crea les relgles
            rutes.set_rules()

        elif argument == "3":
            # Imprimeix les regles a partir d'uns paràmetres
            rutes.print_rules()

        elif argument == "4":
            # Descarga el resultat obtingut a la màquina virtual.
            rutes.download_csv_result()

        elif argument == "5":
            conn = rutes.connect()
            rutes.transformacio_sql()
            dataframe = rutes.get_rules()
                #Versió per crear la pròpia taula i pujar-la, està descartat
                #rutes.create_database()
                #nom_taula = rutes.get_nom_taula()

            for index_fila,fila in dataframe.iterrows():
                query = """
                INSERT into tfmpausalas_taula_regles(date, franja, antecedent, consequent, antecedent_support, consequent_support, support, confidence, lift, leverage, conviction) values('%s', '%s' ,'%s','%s',%s,%s,%s,%s,%s,%s,%s);
                """% ( str(self.dia), str(self.franja), str(fila['antecedents']), str(fila['consequents']), str(fila['antecedent support']), str(fila['consequent support']), str(fila['support']),
                str(fila['confidence']), str(fila['lift']), str(fila['leverage']), str(fila['conviction']))
                #print(query)
                rutes.single_insert(conn, query)
                #Close the connection
            conn.close()



        elif argument == "exit":
            print("Sortint del programa")
        else:
            print("Error")


    def print_menu(self):
        """
        Menu per elegir l'opció
        """
        print("-----------Visualitzador del menú---------------")
        print("Inserti 1 per obtenir un itemset freqüent")
        print("Inserti 2 crear el cojunt de regles a partir d'un itemset freqüent")
        print("Inserti 3 per visualitzar el conjunt de regles")
        print("Inserti 4 per guardar una copia csv del resultat en la màquina virtual")
        print("Inserti 5 per pujar el dataframe resultat a la base de dades Postgres")
        print("Inserti exit per sortir del programa")
        print("------------------------------------------------")

# Per pujar la taula a la base de dades

    def connect(self):
        """
        Connect to the PostgreSQL database server
        """
        conn = None
        try:
            # connect to the PostgreSQL server
            print('Connecting to the PostgreSQL database...')
            conn = psycopg2.connect("dbname='-' user='-' host='-' password='-'")
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            #sys.exit(1)
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
            #Causa per no omplir de logs la memòria
            conn.close()
            # Provoca un error
            return 1
        cursor.close()



    def create_database(conn, self):
        """
        Creació de la taula a la base de dades, decartat
        """
        try:
            cursor = conn.cursor()

            self.nom_taula = input("Introdueix el nom de la taula a crear:")


            create_table_query = '''CREATE TABLE {}
                  (id INT PRIMARY KEY     NOT NULL,
                    date TEXT NOT NULL,
                    antecedent TEXT NOT NULL,
                    consequent TEXT NOT NULL,
                    antecedent_support FLOAT NOT NULL,
                    consequent_support FLOAT NOT NULL,
                    support FLOAT NOT NULL,
                    confidence FLOAT NOT NULL,
                    lift FLOAT NOT NULL,
                    leverage FLOAT NOT NULL,
                    conviction FLOAT NOT NULL); '''.format(nom_taula)

            cursor.execute(create_table_query)
            conn.commit()
            print("Taula creada perfectament a PostgreSQL ")


        except (Exception, psycopg2.DatabaseError) as error :
                print ("Error while creating PostgreSQL table", error)
        finally:
            #closing database connection.
                if(conn):
                    cursor.close()
                    print("Creació de la taula finalitzat")

    def get_nom_taula(self):
        """
        Retorna el nóm de la taula_de_dades
        """
        return self.nom_taula

def seleccio_franja(dia_setmana):
    """
    L'usuari selecciona la franja de temps on executarà l'algoritme
    """
    opcio = 0
    if dia_setmana == "Saturday" or dia_setmana == "Sunday":
        print("Aquest dia està en la franja de cap de setmana, així que eligeix entre descans o entreteniment")
        opcio = input("Elegeix opció descans o entreteniment:   ")
        while opcio != "descans" and opcio != "entreteniment": #Control d'errors d'input
            print("Input incorrecte")
            opcio = input("Elegeix opció descans o entreteniment:   ")
    else:
        print("Aquest dia està entre setmana, així que es pot elegir qualsevol franja")
        opcio = input("Elegeix opció descans, feina o entreteniment:   ")
        while  opcio != "descans" and opcio != "entreteniment" and  opcio != "feina":  #Control d'errors d'input
            print("Input incorrecte:  {} ".format(opcio))
            opcio = input("Elegeix opció descans, feina o entreteniment:   ")
    return opcio


# main
if __name__ == "__main__":
    # execute only if run as a script

    #Variable inici main
    starttime = time.time()
    #Per realitzar probes en local
    memoria = psutil.virtual_memory()
    #dataframe = pd.read_csv('observacionsEstiu20190724mod.csv',sep=';')
    #dataframe = dataframe[:(400000)] #Solament per comprovar el funcionament de l'algoritme

    dataframe = pd.read_csv('observacions_dia.csv')

    #franja = "demati" # Franja seleccionada per realitzar l'estudi

    temps_base = dataframe['seentime'].iloc[0]
    temps = time.gmtime(temps_base)
    temps_string = "{}_{}_{}".format(temps.tm_mday, temps.tm_mon, temps.tm_year)
    #Per obtenir el dia de la setmana en String
    temps_ingles = "{}-{}-{}".format(temps.tm_year, temps.tm_mon, temps.tm_mday)
    dia_setmana = pd.Timestamp(temps_ingles)
    dia_setmana = dia_setmana.day_name()
    print("Dia seleccionat cau en {}".format(dia_setmana))
    #print(df.dayofweek, df.weekday_name)
    franja = seleccio_franja(dia_setmana)


    aps_informacio = pd.read_csv('distribucioapsampliat.csv',sep=',')
    #classificacio_usuaris = pd.read_csv('classificacio_usuaris_mobilitat_{}.csv'.format(temps_string),sep=',')
    #classificacio_usuaris = pd.read_csv('classificacio_usuaris_mobilitat_23_7_2018.csv',sep=',')
    classificacio_usuaris = pd.read_csv('classificacio_usuaris_primera_part.csv')
    print('Lectura de dades took {} seconds'.format(time.time() - starttime))
    processos=4
    processos_vector = [0,1,2,3]
    #Inicialitzador
    rutes = Classificacio_rutes(dataframe, classificacio_usuaris, aps_informacio, processos, temps_string, franja, dia_setmana)
    rutes.set_dataframe_horaris() # Obté les dades per la franja seleccionada
    print('Creació franja took {} seconds'.format(time.time() - starttime))
    rutes.merge_taules()
    rutes.eliminate_dataframe_inicial()# Elimina el dataframe inicial, ja que no el farem servir i llibera espai
    rutes.set_items_list()
    pool = mp.Pool()
    dades_items_zones = pool.map(rutes.aps_llistat_zona, processos_vector)
    dades_items_zones = [ent for sublist in dades_items_zones for ent in sublist]
    rutes.eliminate_dataframe_merge()
    print('Longitud de les dades: {}'.format(len(dades_items_zones)))

    print("memoria utilitzada: {} en MB".format(memoria.used >> 20))
    rutes.set_dataframe(dades_items_zones)
    del dades_items_zones # Allibera espai de memoria
    print('Part de creació de regles ha tardat: {} seconds'.format(time.time() - starttime))
    #menu per l'usuari
    argument = 0
    print('Creació itemsets took {} seconds'.format(time.time() - starttime))
    while argument != "exit":
        rutes.print_menu()
        argument = input("Introdueix una opció del menú:")
        rutes.switch_menu(argument)
