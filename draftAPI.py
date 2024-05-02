from requests.auth import HTTPBasicAuth
from http.client import responses
import requests
import datetime
import socket
import traceback

HOST = "192.168.20.144"  # The IP Address of Translator SIP 
PORT = 6001  # The port used by Translator SIP

library_name = "Library University"
language = "001"

def gettime():
    return datetime.datetime.now().strftime("%Y%m%d    %H%M%S")

def logtime():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
while True:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            print(logtime(), "Ready to Connect")
            conn, addr = s.accept()
            with conn:
                print(logtime(),f"Connected by {addr}")
                while True:
                    data = conn.recv(1024)
                    string = data.decode('utf-8')
                    print(logtime(),string)
                    if not data:
                        break

                    resp = bytes("", "utf-8")
                    title = ""
                    item_id = ""
                    user_id = ""

                    # SC registration
                    if string[0:2] == "99":
                        print(logtime(),"SC registration")
                        resp = bytes("98YYYNNN500   003"+gettime()+"2.00AO"+library_name+"|BXNYYNYNNYNNYNNNNN"+"\r", 'utf-8')

                    # patron end session
                    elif string[0:2] == "35":
                        print(logtime(),"Patron End Session")
                        # get user ID
                        user_id = string.split("AA")[1].split("|")[0]
                        resp = bytes("36Y"+gettime()+"|AO"+library_name+"|AA"+str(user_id)+"\r", 'utf-8')
                        
                    # item information
                    elif string[0:2] == "17":
                        print(logtime(),"Item Information")
                        # get book ID
                        item_id = string.split("AB")[1].split("|")[0]
                        
                        # get book information
                        URL1 = "http://library.ac.id/getbook"
                        headers = {'Accept': 'application/json'}
                        auth = HTTPBasicAuth('apikey', '1234abcd')
                        PARAMS1 = {'buku' : item_id}
                        cek_buku = requests.get(url = URL1, params = PARAMS1, headers=headers, auth=auth)
                        myresult = cek_buku.json()
                        
                        #check response
                        print(logtime(),'Response code cek buku : ',str(cek_buku.status_code))
                        if (cek_buku.status_code) == 200 or (cek_buku.status_code) == 201 :
                            resp = bytes("18000001"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AJ|AFBUKU TIDAK DITEMUKAN"+"\r", 'utf-8')
                            
                        else :
                        # parsing json
                            title = data['results'][0]['judul']
                            status = data['results'][0]['status']
                            due_date = data['results'][0]['batas']

                            # for circulation status
                            loaned = False
                            if status == "dipinjam":
                                loaned = True
                                
                            if loaned :
                                cs = "02"
                                # Form data
                                resp = bytes("18"+cs+"0001"+gettime()+"AO"+library_name+"|AH"+due_date.strftime('%Y-%m-%d')+"|AB"+str(item_id)+"|AJ"+title+"\r", 'utf-8')

                            else:
                                cs = "03"
                                # Form data
                                resp = bytes("18"+cs+"0001"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AJ"+title+"\r", 'utf-8')                    

                    # patron status
                    elif string[0:2] == "23":
                        print(logtime(),"Patron Status")
                        # get user ID
                        user_id = string.split("AA")[1].split("|")[0]
                        
                        # check user
                        URL2 = "http://library.ac.id/getnim"
                        headers = {'Accept': 'application/json'}
                        auth = HTTPBasicAuth('apikey', '1234abcd')
                        PARAMS2 = {'nim' : user_id}
                        cek_user = requests.get(url = URL2, params = PARAMS2, headers=headers, auth=auth)
                        myresult = cek_user.json()

                        print(logtime(),'Response code cek anggota : ',str(cek_user.status_code))
                        if (cek_user.status_code) == 200 or (cek_user.status_code) == 201 :
                            resp = bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|BLN|AFANGGOTA TIDAK DITEMUKAN"+"\r", 'utf-8')
                        else :
                            #parsing json
                            name = data['results'][0]['nama']
                            expdate = data['results'][0]['berakhir']
                            denda = data['results'][0]['denda']

                            if datetime.datetime.date(datetime.datetime.now()) > datetime.datetime.date(expdate):
                                resp = bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANGGOTA TIDAK AKTIF"+"\r", 'utf-8')

                            if denda != 0:
                                resp = bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANDA DIKENAKAN DENDA, SILAHKAN HUBUNGI MEJA SIRKULASI"+"\r", 'utf-8')    
                            else:
                                resp = bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLY"+"\r", 'utf-8')

                    # patron information
                    elif string[0:2] == "63":
                        print(logtime(),"Patron Information")
                        # get user ID
                        user_id = string.split("AA")[1].split("|")[0]
                        
                        # check user
                        URL2 = "http://library.ac.id/getnim"
                        headers = {'Accept': 'application/json'}
                        auth = HTTPBasicAuth('apikey', '1234abcd')
                        PARAMS2 = {'nim' : user_id}
                        cek_user = requests.get(url = URL2, params = PARAMS2, headers=headers, auth=auth)
                        myresult = cek_user.json()

                        print(logtime(),'Response code cek user (PI) : ',str(cek_user.status_code))
                        if (cek_user.status_code) == 200 or (cek_user.status_code) == 201 :
                            resp = bytes("64              001"+gettime()+(" "*24)+"AO"+library_name+"|BLN|AFANGGOTA TIDAK ADA"+"\r","utf-8")
                        else :
                        #parsing json
                            name = data['results'][0]['nama']
                            expdate = data['results'][0]['berakhir']
                            denda = data['results'][0]['denda']
                            barcode_buku = data['results'][0]['pinjaman']
                            if datetime.datetime.date(datetime.datetime.now()) > datetime.datetime.date(expdate):
                                resp = bytes("64              001"+gettime()+(" "*24)+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANGGOTA TIDAK AKTIF"+"\r","utf-8")
                                loan_count=len(barcode_buku)
                                charged_item = ""
                                for id in id_barcode_buku:
                                    charged_item += "|AU"+id

                                resp = bytes("64  "+summary+"           001"+gettime()+(" "*8)+"   "+str(loan_count)+(" "*12)+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BHIDR"+"|BV"+str(denda)+charged_item+"|BLY"+"\r","utf-8")
				
                    # check out
                    elif string[0:2] == "11":
                        print(logtime(),"Checkout")
                        # get user id and item id
                        user_id = string.split("AA")[1].split("|")[0]
                        item_id = string.split("AB")[1].split("|")[0]
						
                        # check user
                        URL2 = "http://library.ac.id/getnim"
                        headers = {'Accept': 'application/json'}
                        auth = HTTPBasicAuth('apikey', '1234abcd')
                        PARAMS2 = {'nim'  : user_id}
                        cek_user = requests.get(url = URL2, params = PARAMS2, headers=headers, auth=auth)
                        myresult = cek_user.json()
                        
                        #parsing json
                        denda = data['results'][0]['denda']

                        if denda != 0:
                            resp = bytes("120NNN"+gettime()+"AO"+library_name+"|AA"+str(user_id)+"AH|AB"+str(item_id)+"|AJ|AFANDA DIKENAKAN DENDA, SILAHKAN HUBUNGI MEJA SIRKULASI"+"\r", 'utf-8')
                            
                        else :
                        # get book information
                            URL1 = "http://library.ac.id/getbook"
                            headers = {'Accept': 'application/json'}
                            auth = HTTPBasicAuth('apikey', '1234abcd')
                            PARAMS1 = {'buku' : item_id}
                            cek_buku = requests.get(url = URL1, params = PARAMS1, headers=headers, auth=auth)
                            myresult = cek_buku.json()
                            
                            # parsing json
                            title = data['results'][0]['judul']
                            
                            #Post Check Out
                            # Define new data to create
                            new_pinjam = {
                            "NIM": user_id,
                            "Buku": item_id 
                            }
                            
                            # The API endpoint to communicate with
                            URL3 = "http://library.ac.id/pinjam"
                            headers = {'Accept': 'application/json'}
                            auth = HTTPBasicAuth('apikey', '1234abcd')
                            
                            # A POST request to the API
                            pinjam = requests.post(url = URL3, json=new_pinjam, headers=headers, auth=auth)
                            
                            # Print the response
                            print(logtime(),'Response code Peminjaman : ',str(pinjam.status_code))\
                            
                            if (pinjam.status_code) == 200 or (pinjam.status_code) == 201:
                                resp = bytes("121NNY"+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AH"+str((datetime.datetime.now() + datetime.timedelta(days=loan_periode)).strftime('%Y-%m-%d'))+"|AB"+str(item_id)+"|AJ"+title+"|AFBUKU BERHASIL DIPINJAM"+"\r", 'utf-8')
                            else :
                                resp = bytes("120NNN"+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AH|AB"+str(item_id)+"|AJ"+title+"|AFBUKU GAGAL DIPINJAM"+"\r", 'utf-8')
                            
      # check in
                    elif string[0:2] == "09":
                        print(logtime(),"Checkin")
                        returnY = string[3:7]
                        returnM = string[7:9]
                        returnD = string[9:11]
                        print(logtime(),returnY, returnM, returnD)
                        item_id = string.split("AB")[1].split("|")[0]
                        print(item_id)
                        
                        # check user
                        URL2 = "http://library.ac.id/getnim"
                        headers = {'Accept': 'application/json'}
                        auth = HTTPBasicAuth('apikey', '1234abcd')
                        PARAMS2 = {'nim' : user_id}
                        cek_user = requests.get(url = URL2, params = PARAMS2, headers=headers, auth=auth)
                        myresult = cek_user.json()
                        
                        #parsing json
                        denda = data['results'][0]['denda']
                        
                        if denda != 0:
                            resp = bytes("100NNY"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AQ|AJ"+title+"|AFANDA MENDAPAT DENDA, SILAHKAN KE SIRKULASI"+"\r", 'utf-8')
                            
                        else :
                            # get book information
                            URL1 = "http://library.ac.id/getbook"
                            headers = {'Accept': 'application/json'}
                            auth = HTTPBasicAuth('apikey', '1234abcd')
                            PARAMS1 = {'buku' : item_id}
                            cek_buku = requests.get(url = URL1, params = PARAMS1, headers=headers, auth=auth)
                            myresult = cek_buku.json()
                            
                            # parsing json
                            title = data['results'][0]['judul']
                            
                            #Post Check In
                            # Define new data to create
                            new_kembali = {
                            "Buku": item_id 
                            }
                            
                            # The API endpoint to communicate with
                            URL4 = "http://library.ac.id/kembali"
                            headers = {'Accept': 'application/json'}
                            auth = HTTPBasicAuth('apikey', '1234abcd')
                            
                            # A POST request to the API
                            kembali = requests.put(url = URL4, json=new_kembali, headers=headers, auth=auth)
                            
                            # Print the response
                            print(logtime(),'Response code Pengembalian : ',str(kembali.status_code))
                            
                            if (kembali.status_code) == 200 or (kembali.status_code) == 201 :
                                resp = bytes("101YNN"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AQ|AJ"+title+"|AFBUKU BERHASIL DIKEMBALIKAN"+"\r", 'utf-8')
                            else :
                                resp = bytes("100NNY"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AQ|AJ"+title+"|AFBUKU GAGAL DIKEMBALIKAN"+"\r", 'utf-8')
                                
                    print(logtime(),resp)
                    conn.sendall(resp)
                    
    except Exception as error:
        print(logtime(),traceback.format_exc())
