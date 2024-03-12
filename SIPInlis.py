import mysql.connector
import datetime
import socket
import traceback

HOST = "192.168.20.144"  # The IP Address of Translator SIP 
PORT = 6001  # The port used by Translator SIP

library_name = ""
language = "001"
slims_version = "Inlis" # Please select the version

db_host="127.0.0.1" #IP Address of the database
db_user="root" #db username (read/write) access
db_password="" #db password
db_port="3309" # port used by the db
db_name="inlislite_v3" # name of the db

def gettime():
    return datetime.datetime.now().strftime("%Y%m%d    %H%M%S")

def logtime():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def generate_collectionloanid():    
    try:
        with open('inlis_loan.dat', 'x') as file:
            file.write(datetime.datetime.now().strftime("%y%m%d")+','+'1')
        return "1"+datetime.datetime.now().strftime("%y%m%d")+'1'+'0001'
    
    except FileExistsError:
        # print(f"The file {file_path} already exists.")
        string = ""
        retstring = ""
        with open('inlis_loan.dat', 'r') as file:
            current = file.readlines()
            date = current[0].split(',')[0]
            count = current[0].split(',')[1]
            if date == datetime.datetime.now().strftime("%y%m%d"):
                count = str(int(count)+1)
                string = date + ',' + count
                counts = "0"*(4-len(count))
                retstring = "1"+datetime.datetime.now().strftime("%y%m%d")+'1'+counts+count

            else:
                date = datetime.datetime.now().strftime("%y%m%d")
                string = datetime.datetime.now().strftime("%y%m%d") + ',' + '1'
                retstring = "1"+datetime.datetime.now().strftime("%y%m%d")+'10001'
        with open('inlis_loan.dat', 'w') as file:
            file.write(string)
        
        return retstring


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
                    
                    # item information
                    elif string[0:2] == "17":
                        print(logtime(),"Item Information")
                        # get book ID
                        item_id = string.split("AB")[1].split("|")[0]

                        # DB Connect
                        try:
                            mydb = mysql.connector.connect(
                            host=db_host, #IP Address of the database
                            user=db_user, #db username (read/write) access
                            password=db_password, #db password
                            port=db_port, # port used by the db
                            database=db_name # name of the db
                            )
                            print(logtime(), "DB Connected")
                        except Exception as error:
                                print(logtime(),traceback.format_exc())
                                
                        # get book information
                        mycursor = mydb.cursor()
                        mycursor.execute("SELECT Catalog_id FROM collections WHERE NomorBarcode='"+item_id+"'")
                        myresult = mycursor.fetchall()

                        if len(myresult) == 0:
                            resp = bytes("18000001"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AJ|AFBUKU TIDAK DITEMUKAN"+"\r", 'utf-8')

                        else :
                            # get title
                            biblio_id = myresult[0][0]
                            mycursor = mydb.cursor()
                            mycursor.execute("SELECT Title FROM catalogs WHERE ID="+str(biblio_id))
                            myresult = mycursor.fetchall()
                            title = myresult[0][0]

                            # for circulation status
                            loaned = False

                            mycursor = mydb.cursor()
                            mycursor.execute("SELECT cl.DueDate FROM collectionloanitems as cl, collections as cs WHERE cs.NomorBarcode = '"+item_id+"' AND cs.ID = cl.Collection_id AND cl.LoanStatus = \"Loan\" ORDER BY LoanDate DESC")
                            myresult = mycursor.fetchall()
                            if len(myresult) != 0:
                                loaned = True
                                
                            if loaned :
                                cs = "02"
                                due_date = myresult[0][0]

                                # Form data
                                resp = bytes("18"+cs+"0001"+gettime()+"AO"+library_name+"|AH"+due_date.strftime('%Y-%m-%d')+"|AB"+str(item_id)+"|AJ"+title+"\r", 'utf-8')

                            else:
                                cs = "03"
                                # Form data
                                resp = bytes("18"+cs+"0001"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AJ"+title+"\r", 'utf-8')
                        mydb.close()
                        print(logtime(),"DB Closed")

                    # patron end session
                    elif string[0:2] == "35":
                        print(logtime(),"Patron End Session")
                        # get user ID
                        user_id = string.split("AA")[1].split("|")[0]
                        resp = bytes("36Y"+gettime()+"|AO"+library_name+"|AA"+str(user_id)+"\r", 'utf-8')
                    
                    # patron status
                    elif string[0:2] == "23":
                        print(logtime(),"Patron Status")
                        # get user ID
                        user_id = string.split("AA")[1].split("|")[0]

                        # DB Connect
                        try:
                            mydb = mysql.connector.connect(
                            host=db_host, #IP Address of the database
                            user=db_user, #db username (read/write) access
                            password=db_password, #db password
                            port=db_port, # port used by the db
                            database=db_name # name of the db
                            )
                            print(logtime(), "DB Connected")
                        except Exception as error:
                                print(logtime(),traceback.format_exc())

                        # check user
                        mycursor = mydb.cursor()
                        mycursor.execute("SELECT Fullname, EndDate FROM members WHERE MemberNo='"+user_id+"'")
                        myresult = mycursor.fetchall()

                        if len(myresult) == 0:
                            resp = bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|BLN|AFANGGOTA TIDAK DITEMUKAN"+"\r", 'utf-8')
                        else :
                            name = myresult[0][0]
                            expdate = myresult[0][1]
                            if datetime.datetime.date(datetime.datetime.now()) > datetime.datetime.date(expdate):
                                resp = bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANGGOTA TIDAK AKTIF"+"\r", 'utf-8')
                            
                            mycursor = mydb.cursor()
                            mycursor.execute("SELECT LoanReturnLateCount from members WHERE MemberNo='"+user_id+"'")
                            myresult = mycursor.fetchall()

                            if myresult[0][0] != 0:
                                resp = bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANDA DIKENAKAN DENDA, SILAHKAN HUBUNGI MEJA SIRKULASI"+"\r", 'utf-8')    
                            else:
                                resp = bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLY"+"\r", 'utf-8')

                        mydb.close()
                        print(logtime(),"DB Closed")

                    # patron information
                    elif string[0:2] == "63":
                        print(logtime(),"Patron Information")
                        # get user ID
                        user_id = string.split("AA")[1].split("|")[0]

                        # DB Connect
                        try:
                            mydb = mysql.connector.connect(
                            host=db_host, #IP Address of the database
                            user=db_user, #db username (read/write) access
                            password=db_password, #db password
                            port=db_port, # port used by the db
                            database=db_name # name of the db
                            )
                            print(logtime(), "DB Connected")
                        except Exception as error:
                                print(logtime(),traceback.format_exc())

                        # check user
                        mycursor = mydb.cursor()
                        mycursor.execute("SELECT Fullname, EndDate FROM members WHERE MemberNo='"+user_id+"'")
                        myresult = mycursor.fetchall()
                        if len(myresult) == 0:
                            resp = bytes("64              001"+gettime()+(" "*24)+"AO"+library_name+"|BLN|AFANGGOTA TIDAK ADA"+"\r","utf-8")
                        else :
                            name = myresult[0][0]
                            expdate = myresult[0][1]
                            if datetime.datetime.date(datetime.datetime.now()) > datetime.datetime.date(expdate):
                                resp = bytes("64              001"+gettime()+(" "*24)+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANGGOTA TIDAK AKTIF"+"\r","utf-8")
                            
                            mycursor = mydb.cursor()
                            mycursor.execute("SELECT LoanReturnLateCount from members WHERE MemberNo='"+user_id+"'")
                            myresult = mycursor.fetchall()

                            if myresult[0][0] != 0:
                                resp = bytes("64              001"+gettime()+(" "*24)+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANDA DIKENAKAN DENDA, SILAHKAN HUBUNGI MEJA SIRKULASI"+"\r","utf-8")
                            else:
                                loan_count = 0
                                summary = " "
                                id_list_loan = []

                                mycursor = mydb.cursor()
                                mycursor.execute("SELECT cl.Collection_id FROM collectionloanitems as cl, members as mb WHERE cl.LoanStatus=\"Loan\" and cl.member_id=mb.ID and MemberNo='"+user_id+"' ORDER BY cl.CreateDate DESC")
                                myresult = mycursor.fetchall()
                                if len(myresult) != 0:
                                    for x in myresult:
                                        loan_count += 1
                                        mycursor.execute("SELECT NomorBarcode FROM collections WHERE ID='"+str(x[0])+"'")
                                        tempresult = mycursor.fetchall()
                                        id_list_loan.append(tempresult[0][0])
                                        summary = "Y"
                                
                                charged_item = ""
                                for id in id_list_loan:
                                    charged_item += "|AU"+id

                                resp = bytes("64  "+summary+"           001"+gettime()+(" "*8)+"   "+str(loan_count)+(" "*12)+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+charged_item+"|BLY"+"\r","utf-8")

                        mydb.close()
                        print(logtime(),"DB Closed")

                    # check out
                    elif string[0:2] == "11":
                        print(logtime(),"Checkout")
                        # get user id and item id
                        user_id = string.split("AA")[1].split("|")[0]
                        item_id = string.split("AB")[1].split("|")[0]

                        # DB Connect
                        try:
                            mydb = mysql.connector.connect(
                            host=db_host, #IP Address of the database
                            user=db_user, #db username (read/write) access
                            password=db_password, #db password
                            port=db_port, # port used by the db
                            database=db_name # name of the db
                            )
                            print(logtime(), "DB Connected")
                        except Exception as error:
                                print(logtime(),traceback.format_exc())

                        mycursor = mydb.cursor()
                        mycursor.execute("SELECT LoanReturnLateCount from members WHERE MemberNo='"+user_id+"'")
                        myresult = mycursor.fetchall()

                        if myresult[0][0] != 0:
                            resp = bytes("120NNN"+gettime()+"AO"+library_name+"|AA"+str(user_id)+"AH|AB"+str(item_id)+"|AJ|AFANDA DIKENAKAN DENDA, SILAHKAN HUBUNGI MEJA SIRKULASI"+"\r", 'utf-8')
                            
                        else :
                            # get member type
                            mycursor = mydb.cursor()
                            mycursor.execute("SELECT JenisAnggota_id, ID FROM members WHERE MemberNo='"+user_id+"'")
                            myresult = mycursor.fetchall()
                            member_type = myresult[0][0]
                            member_id = myresult[0][1]

                            # get max loan, and loan duration
                            mycursor = mydb.cursor()
                            mycursor.execute("SELECT MaxPinjamKoleksi, maxLoanDays FROM jenis_anggota WHERE id='"+str(member_type)+"'")
                            myresult = mycursor.fetchall()
                            
                            loan_limit = myresult[0][0]
                            loan_periode = myresult[0][1]
                            
                            # check loan limit
                            mycursor = mydb.cursor()
                            mycursor.execute("SELECT cl.CollectionLoan_id FROM collectionloanitems as cl, members as mb WHERE cl.LoanStatus=\"Loan\" and cl.member_id=mb.ID and MemberNo='"+user_id+"' ORDER BY cl.CreateDate DESC")
                            myresult = mycursor.fetchall()
                            loan = 0
                            if len(myresult) != 0:
                                for x in myresult:
                                    loan += 1
                        
                            if loan == loan_limit:
                                resp = bytes("120NNN"+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AH|AB"+str(item_id)+"|AJ|AFSUDAH MENCAPAI LIMIT PEMINJAMAN"+"\r", 'utf-8')
                            
                            else:
                                # check book
                                mycursor = mydb.cursor()
                                mycursor.execute("SELECT Catalog_id, ID FROM collections WHERE NomorBarcode='"+item_id+"'")
                                myresult = mycursor.fetchall()
                                if len(myresult) == 0 :
                                    resp = bytes("120NNN"+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AH|AB"+str(item_id)+"|AJ|AFBUKU TIDAK DITEMUKAN"+"\r", 'utf-8')
                                else :
                                    # get title
                                    biblio_id = myresult[0][0]
                                    collection_id = myresult[0][1]
                                    mycursor = mydb.cursor()
                                    mycursor.execute("SELECT Title FROM catalogs WHERE ID="+str(biblio_id))
                                    myresult = mycursor.fetchall()
                                    title = myresult[0][0]

                                    # for circulation status
                                    loaned = False

                                    mycursor = mydb.cursor()
                                    mycursor.execute("SELECT cl.DueDate FROM collectionloanitems as cl, collections as cs WHERE cs.NomorBarcode = '"+item_id+"' AND cs.ID = cl.Collection_id AND cl.LoanStatus = \"Loan\" ORDER BY LoanDate DESC")
                                    myresult = mycursor.fetchall()
                                    if len(myresult) != 0:
                                        loaned = True

                                    if loaned:
                                        resp = bytes("120NNN"+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AH|AB"+str(item_id)+"|AJ"+title+"|AFBUKU SUDAH DIPINJAM"+"\r", 'utf-8')
                                    else :
                                        resp = bytes("121NNY"+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AH"+str((datetime.datetime.now() + datetime.timedelta(days=loan_periode)).strftime('%Y-%m-%d'))+"|AB"+str(item_id)+"|AJ"+title+"|AFBUKU BERHASIL DIPINJAM"+"\r", 'utf-8')
                                        cid = generate_collectionloanid()    
                                        # insert to loan
                                        sql = "INSERT INTO collectionloans (ID, CollectionCount, member_id, CreateDate, UpdateDate, LocationLibrary_id) VALUES (%s, %s, %s, %s, %s, %s)"
                                        val = (cid, 1,  member_id, datetime.datetime.now().strftime('%Y-%m-%d'), datetime.datetime.now().strftime('%Y-%m-%d'), 1)
                                        
                                        mycursor.execute(sql, val)
                                        
                                        mydb.commit()

                                        print(logtime(),mycursor.rowcount, "record inserted.")
                                        print(logtime(),mycursor._warnings)
                                        
                                        sql = "INSERT INTO collectionloanitems (CollectionLoan_id, LoanDate, DueDate, LoanStatus, Collection_id, member_id, CreateDate, UpdateDate) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                                        val = (cid,datetime.datetime.now().strftime('%Y-%m-%d'), (datetime.datetime.now() + datetime.timedelta(days=loan_periode)).strftime('%Y-%m-%d'), "Loan", collection_id, member_id, datetime.datetime.now().strftime('%Y-%m-%d'), datetime.datetime.now().strftime('%Y-%m-%d'))

                                        mycursor.execute(sql, val)

                                        mydb.commit()

                                        print(logtime(),mycursor.rowcount, "record inserted.")
                                        print(logtime(),mycursor._warnings)


                                        if slims_version == 9:
                                            # insert to log
                                            sql = "INSERT INTO system_log (log_type, id, log_location, sub_module, action, log_msg, log_date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                                            val = ("system", user_id, "circulation", "Loan", "Add", "Gateway: Loan", datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                                            mycursor.execute(sql, val)

                                            mydb.commit()

                                            print(logtime(),mycursor.rowcount, "record inserted.")
                                            print(logtime(),mycursor._warnings)
                                    
                        mydb.close()
                        print(logtime(),"DB Closed")
                            
                    # check in
                    elif string[0:2] == "09":
                        print(logtime(),"Checkin")
                        returnY = string[3:7]
                        returnM = string[7:9]
                        returnD = string[9:11]
                        print(logtime(),returnY, returnM, returnD)
                        item_id = string.split("AB")[1].split("|")[0]
                        print(item_id)

                        # DB Connect
                        try:
                            mydb = mysql.connector.connect(
                            host=db_host, #IP Address of the database
                            user=db_user, #db username (read/write) access
                            password=db_password, #db password
                            port=db_port, # port used by the db
                            database=db_name # name of the db
                            )
                            print(logtime(), "DB Connected")
                        except Exception as error:
                                print(logtime(),traceback.format_exc())

                        # Check fines
                        mycursor = mydb.cursor()
                        mycursor.execute("SELECT cl.DueDate from collectionloanitems as cl, collections as cs where cl.Collection_id=cs.ID and cs.NomorBarcode='"+item_id+"' AND TO_DAYS(duedate) < TO_DAYS(NOW())")
                        myresult = mycursor.fetchall()

                        if len(myresult) != 0:
                            resp = bytes("100NNY"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AQ|AJ"+title+"|AFANDA MENDAPAT DENDA, SILAHKAN KE SIRKULASI"+"\r", 'utf-8')

                        else:
                            # check book
                            mycursor = mydb.cursor()
                            mycursor.execute("SELECT Catalog_id, ID FROM collections WHERE NomorBarcode='"+item_id+"'")
                            print("NomorBarcode= ",item_id)
                            myresult = mycursor.fetchall()
                            if len(myresult) == 0 :
                                resp = bytes("100NNY"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AQ|AJ"+title+"|AFBUKU TIDAK DITEMUKAN"+"\r", 'utf-8')

                            else :
                                # get title
                                biblio_id = myresult[0][0]
                                collection_id = myresult[0][1]
                                print("Collection_id=",collection_id)
                                mycursor = mydb.cursor()
                                mycursor.execute("SELECT Title FROM catalogs WHERE ID="+str(biblio_id))
                                myresult = mycursor.fetchall()
                                title = myresult[0][0]

                                loaned = False
                                mycursor = mydb.cursor()
                                mycursor.execute("SELECT cl.DueDate FROM collectionloanitems as cl, collections as cs WHERE cs.NomorBarcode = '"+item_id+"' AND cs.ID = cl.Collection_id AND cl.LoanStatus = \"Loan\" ORDER BY LoanDate DESC")
                                myresult = mycursor.fetchall()
                                due = myresult[0][0]
                                if len(myresult) != 0:
                                    loaned = True

                                    if not loaned:   
                                        resp = bytes("100NNN"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AQ|AJ"+title+"|AFBUKU BELUM DIPINJAM"+"\r", 'utf-8')
                                    
                                    else:
                                        resp = bytes("101YNN"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AQ|AJ"+title+"|AFBUKU BERHASIL DIKEMBALIKAN"+"\r", 'utf-8')

                                        # update to loan
                                        sql = "UPDATE collectionloanitems SET LoanStatus=%s, UpdateDate=%s, ActualReturn=%s, LateDays=TO_DAYS(DueDate) - TO_DAYS(NOW()) WHERE LoanStatus=\"Loan\" AND Collection_id=%s"
                                        val = ("Return", returnY + "-" + returnM + "-" + returnD, returnY + "-" + returnM + "-" + returnD, collection_id)

                                        mycursor.execute(sql, val)

                                        mydb.commit()

                                        print(logtime(),mycursor.rowcount, "record inserted.")
                                        print(logtime(),mycursor._warnings)
                                
                                else:
                                    resp = bytes("100NNY"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AQ|AJ"+title+"|AFBUKU BELUM DIPINJAM"+"\r", 'utf-8')

                        mydb.close()
                        print(logtime(),"DB Closed")
                    
                    print(logtime(),resp)
                    conn.sendall(resp)
    except Exception as error:
        print(logtime(),traceback.format_exc())
