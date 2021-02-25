
#Autor Pau Salas Cerda
#Data 25 de febrer de 2021
#Llibreries necessàries
import pandas as pd
from pandas import DataFrame
import time
from multiprocessing import Pool
import multiprocessing as mp
from multiprocessing import Process, Pipe, current_process
import operator
from functools import reduce


class Classificaciodispositius(object):
    """
    Classe per classificar els dispositius
    """
    def __init__(self, dataframe, procesos):
        """
        Constructor
        """
        self.dataframe = dataframe
        self.procesos = procesos
        #super(, self).__init__()
        self.latitude_max =  39.5786
        self.latitude_min = 39.5442
        self.longitude_min = 2.6180
        self.longitude_max = 2.6717

        self.min_contador_habitual = 3
        self.periode_eliminacio = 500

        self.classificacio_usuaris = list()




    def eliminate_error(self, vector):
        """
        Eliminar els possibles errors a les dades
        """

        self.dataframe = self.dataframe.drop(['seendate','model','ssid'],axis = 1)
        self.dataframe = self.dataframe.dropna()
        longitud_dataframe = len(self.dataframe)

        #Reducció de la longitud de les dades.
        dataframe = self.dataframe[(int(0+ (longitud_dataframe*vector/self.procesos))):(int(longitud_dataframe/self.procesos+longitud_dataframe*vector/self.procesos))]

         # Eliminar punts defora de la ciutat de Palma
        for indice_fila, fila  in dataframe.iterrows():
            if self.latitude_max > fila["lat"] and self.latitude_min < fila["lat"] and self.longitude_max > fila["lng"] and self.longitude_min < fila["lng"]:
                self.dataframe = self.dataframe.drop([indice_fila], axis=0)

        print("El procés {} ha eliminat els error de la part {} del dataframe \n".format(current_process().name, vector))

    def get_head (self):
        """
        Per obtenir la capçalera de les dades
        """
        return self.dataframe.head()


    def habitual_esporadic(self, vector):
        """
        Indicació si es esporadic l'usuari o habitual a la xarxa
        """
        valors_usuaris = list()

        #Obtenció del temps en UTC
        temps_base = self.dataframe['seentime'].iloc[0]
        temps = time.gmtime(temps_base)
        temps_string = "{}/{}/{}".format(temps.tm_mday, temps.tm_mon, temps.tm_year)

        llista_usuaris = dispositius.get_llista_usuaris()

        #Divisió de dades per processos.
        longitud_usuaris = len(self.llista_usuaris)
        limit_inferior = int(longitud_usuaris*vector/self.procesos)
        limit_superior = int(longitud_usuaris/self.procesos+longitud_usuaris*vector/self.procesos)
        llista_usuaris = llista_usuaris[(limit_inferior):(limit_superior)]


        for i  in llista_usuaris: #Recorrer les entrades de cada usuari
            entrades_dispositiu = self.dataframe[i == self.dataframe["clientmac"]]
            contador_usuari = 0


            if len(entrades_dispositiu) < self.min_contador_habitual:  # Si no supera el nombre de mostres mínima
                habitual_esporadic = "esporadic"
                mobil_estatic = 'inclassificable'
            else:
                entrades_dispositiu = entrades_dispositiu.sort_values(by=['seentime'])
                ultim_valor = -1

                for indice_fila, fila  in entrades_dispositiu.iterrows():  #Eliminar entrades molt juntes perque no falsifiquin les dades

                    if ultim_valor == -1:
                        ultim_valor = fila['seentime']

                    elif (fila['seentime'] - ultim_valor) > self.periode_eliminacio: #Si les mostres etan molt juntes no es conta
                        contador_usuari = contador_usuari + 1
                        ultim_valor = fila['seentime']

                if contador_usuari > self.min_contador_habitual:
                    habitual_esporadic = "habitual"
                    entrades_aps = entrades_dispositiu.drop_duplicates(subset=['apmac'])
                    if len(entrades_aps) > 1: #És mira si canvia d'AP al llarg del temps per si és mòbil o estàtic
                        mobil_estatic = 'mobil'
                    else:
                        mobil_estatic = 'estatic'
                else:
                    habitual_esporadic = "esporadic"
                    mobil_estatic = 'inclassificable'

            valors = (i,habitual_esporadic, mobil_estatic, temps_string)
            valors_usuaris.append(valors)

        print("El procés {} ha classificat els usuaris de la part {} \n".format(current_process().name, vector))
        print("el procés {} te una longitud de {} \n".format(current_process().name, len(valors_usuaris)))
        return valors_usuaris

    def get_classificacio_usuaris(self):
        """
        retorna la classificació dels usuaris
        """
        return self.classificacio_usuaris

    def get_habitual_esporadic(self):
        """
        Per obtenir el llistat d'habituals i esporàdics
        """
        return self.classificacio_usuaris


    def llista_usuaris(self):
        """
        Obtenció dels dispositius únics
        """
        self.llista_usuaris = self.dataframe.drop_duplicates(subset=['clientmac'])
        self.llista_usuaris = self.llista_usuaris['clientmac']
        print("nombre de dispositius: {}".format(len(self.llista_usuaris)))

    def get_llista_usuaris(self):
        """
        Obtenció de la llista d'usuaris
        """
        return self.llista_usuaris


    def write_csv(self, llistat_usuaris):
        """
        Per escriure un csv amb les dades
        """
        columnes = ["clientmac","class_hab_esp","class_mob_est","dia"]
        #dades_usuari = reduce(operator.concat , llistat_usuaris)
        result = DataFrame(llistat_usuaris , columns = columnes)
        result.to_csv ('classificacio_usuaris_primera_part.csv', index = False, header=True)



# main
if __name__ == "__main__":
    # execute only if run as a script
    starttime = time.time()
    dades_usuaris = []
    #Segons la màquina aquest valor s'ha de canviar o mantenir-se
    processos=4
    processos_vector = [0,1,2,3]

    dataframe = pd.read_csv('observacions_dia.csv',sep=',')
    # dataframe = dataframe[:(100000)] #Solament per comprovar el funcionament de l'algoritme

    dispositius = Classificaciodispositius(dataframe, processos)
    dispositius.llista_usuaris()
    print('Primera part took {} seconds'.format(time.time() - starttime))
    #Execució del multiprocessing.
    pool = mp.Pool()

    dades_usuaris = pool.map(dispositius.habitual_esporadic, processos_vector)# retorna a list of lists
    dades_usuaris = [ent for sublist in dades_usuaris for ent in sublist] #Fuciona el resultat en una llista tota sola
    print('La part multiprocessing a tardat {} seconds'.format(time.time() - starttime))
    print("Longitud de les dades {}".format(len(dades_usuaris)))
    dispositius.write_csv(dades_usuaris) #Escriu un csv que s'utilitzarà en els segúents algoritmes.
    #pool.map(dispositius.multiprocessing_func_eliminar_errors, range(0,8))
    #pool.map(dispositius.multiprocessing_func_classificar_usuaris, range(0,7))

    print('That took {} seconds'.format(time.time() - starttime))
