import mysql.connector
import datetime
import socket
import logging

HOST = "192.168.20.251"  # The IP Address of Translator SIP 
PORT = 6001  # The port used by Translator SIP

library_name = "Perpustakaan"
language = "001"
slims_version = "8"  # Please select the version

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'root',
    'port': '3404',
    'database': 'bulian'
}

def gettime():
    return datetime.datetime.now().strftime("%Y%m%d    %H%M%S")

def logtime():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def connect_db():
    try:
        mydb = mysql.connector.connect(**db_config)
        print(logtime(), "DB Connected")
        return mydb
    except mysql.connector.Error as err:
        logging.error(f"{logtime()} DB Connection Error: {err}")
        return None

def fetch_data(query, params=None):
    db = connect_db()
    if not db:
        return None
    cursor = db.cursor()
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except mysql.connector.Error as err:
        logging.error(f"{logtime()} DB Query Error: {err}")
        return None
    finally:
        cursor.close()
        db.close()
        print(logtime(), "DB Closed")

def handle_sc_registration():
    return bytes("98YYYNNN500   003"+gettime()+"2.00AO"+library_name+"|BXNYYNYNNYNNYNNNNN"+"\r", 'utf-8')

def handle_item_information(item_id):
    query = "SELECT biblio_id FROM item WHERE item_code=%s"
    result = fetch_data(query, (item_id,))
    if not result:
        return bytes("18000001"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AJ|AFBUKU TIDAK DITEMUKAN"+"\r", 'utf-8')

    biblio_id = result[0][0]
    query = "SELECT title FROM biblio WHERE biblio_id=%s"
    title_result = fetch_data(query, (biblio_id,))
    
    if not title_result:
        return bytes("18000001"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AJ|AFBUKU TIDAK DITEMUKAN"+"\r", 'utf-8')

    title = title_result[0][0]
    
    query = "SELECT due_date FROM loan WHERE item_code=%s AND `is_lent`=1 AND `is_return`=0 ORDER BY `loan_id`"
    loan_result = fetch_data(query, (item_id,))
    
    if loan_result:
        due_date = loan_result[0][0]
        return bytes("18"+"02"+"0001"+gettime()+"AO"+library_name+"|AH"+due_date.strftime('%Y-%m-%d')+"|AB"+str(item_id)+"|AJ"+title+"\r", 'utf-8')
    else:
        return bytes("18"+"03"+"0001"+gettime()+"AO"+library_name+"|AB"+str(item_id)+"|AJ"+title+"\r", 'utf-8')

def handle_patron_status(user_id):
    query = "SELECT member_name, expire_date FROM member WHERE member_id=%s"
    result = fetch_data(query, (user_id,))
    if result is None:
        return bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|BLN|AFANGGOTA TIDAK DITEMUKAN"+"\r", 'utf-8')
    
    if not result:
        return bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|BLN|AFANGGOTA TIDAK DITEMUKAN"+"\r", 'utf-8')
    
    name, expdate = result[0]
    
    if datetime.datetime.date(datetime.datetime.now()) > expdate:
        return bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANGGOTA TIDAK AKTIF"+"\r", 'utf-8')

    query = "SELECT loan_id FROM loan WHERE is_lent=1 AND is_return=0 AND TO_DAYS(due_date) < TO_DAYS(NOW()) AND member_id=%s"
    overdue_loans = fetch_data(query, (user_id,))

    if overdue_loans:
        return bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANDA DIKENAKAN DENDA, SILAHKAN HUBUNGI MEJA SIRKULASI"+"\r", 'utf-8')

    return bytes("24"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLY"+"\r", 'utf-8')

def handle_checkout(user_id, item_id):
    try:
        print(logtime(), "DB Connected")
    except Exception as error:
        logging.error(f"{logtime()} DB Connection Error: {error}")
        return bytes("12"+" "*14+language+gettime()+"AO"+library_name+"|AA"+str(user_id)+"|AB"+str(item_id)+"|AFGAGAL MELAKUKAN PEMINJAMAN"+"\r", 'utf-8')

    # Cek apakah anggota memiliki denda
    query = "SELECT loan_id FROM loan WHERE is_lent=1 AND is_return=0 AND TO_DAYS(due_date) < TO_DAYS(NOW()) AND member_id=%s"
    myresult = fetch_data(query, (user_id,))
    
    if myresult and len(myresult) != 0:
        return bytes("120NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AH|AB" + str(item_id) + "|AJ|AFANDA DIKENAKAN DENDA, SILAHKAN HUBUNGI MEJA SIRKULASI" + "\r", 'utf-8')

    # Mendapatkan tipe anggota
    query = "SELECT member_type_id FROM member WHERE member_id=%s"
    myresult = fetch_data(query, (user_id,))
    member_type = myresult[0][0]

    # Mendapatkan batasan peminjaman dan periode peminjaman
    query = "SELECT loan_limit, loan_periode FROM mst_member_type WHERE member_type_id=%s"
    myresult = fetch_data(query, (str(member_type),))
    loan_limit = myresult[0][0]
    loan_periode = myresult[0][1]

    # Mendapatkan jumlah pinjaman saat ini
    query = "SELECT item_code FROM loan WHERE member_id=%s AND is_lent=1 AND is_return=0 ORDER BY loan_id"
    myresult = fetch_data(query, (user_id,))
    loan = len(myresult)

    if loan == loan_limit:
        return bytes("120NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AH|AB" + str(item_id) + "|AJ|AFSUDAH MENCAPAI LIMIT PEMINJAMAN" + "\r", 'utf-8')

    # Cek apakah item ada dalam database and coll_type_id not 1 itu karena coll_type_id yg nilainya 1 di tabel item itu buku referensi yang nggak boleh dipinjam, seperti di UNJ.
    query = "SELECT biblio_id FROM item WHERE  item_code='"+item_id+"' AND coll_type_id NOT LIKE '1'"
    myresult = fetch_data(query, (item_id,))
    
    if not myresult:
        return bytes("120NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AH|AB" + str(item_id) + "|AJ|AFBUKU TIDAK DITEMUKAN" + "\r", 'utf-8')

    biblio_id = myresult[0][0]
    coll_type_id = myresult[0][1]

    # Mendapatkan judul buku
    query = "SELECT title FROM biblio WHERE biblio_id=%s"
    myresult = fetch_data(query, (str(biblio_id),))
    title = myresult[0][0]

    # Mendapatkan aturan peminjaman
    query = "SELECT loan_rules_id FROM mst_loan_rules WHERE member_type_id=%s AND coll_type_id=%s"
    loan_rules_result = fetch_data(query, (member_type, coll_type_id))
    
    if not loan_rules_result:
        return bytes("120NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AH|AB" + str(item_id) + "|AJ|AFLOAN RULES NOT FOUND" + "\r", 'utf-8')

    loan_rules_id = loan_rules_result[0][0]

    # Cek apakah item sudah dipinjam
    query = "SELECT due_date FROM loan WHERE item_code=%s AND is_lent=1 AND is_return=0 ORDER BY loan_id"
    loan_result = fetch_data(query, (item_id,))
    loaned = len(loan_result) != 0

    if loaned:
        query = "SELECT l.item_code FROM reserve AS rs INNER JOIN loan AS l ON rs.item_code = l.item_code WHERE l.item_code = %s AND l.member_id != %s"
        reserved_result = fetch_data(query, (item_id, user_id))

        if reserved_result:
            return bytes("300NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AB" + str(item_id) + "|AJ|AFITEM DITAHAN OLEH ANGGOTA LAIN" + "\r", 'utf-8')

    # Buku belum dipinjam, lanjutkan peminjaman
    return bytes("121NNY" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AH" + str((datetime.datetime.now() + datetime.timedelta(days=loan_periode)).strftime('%Y-%m-%d')) + "|AB" + str(item_id) + "|AJ" + title + "|AFBUKU BERHASIL DIPINJAM" + "\r", 'utf-8')

    # Masukkan data peminjaman ke database
    query = """
        INSERT INTO loan (item_code, member_id, loan_date, due_date, loan_rules_id, is_lent)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    val = (item_id, user_id, datetime.datetime.now().strftime('%Y-%m-%d'), 
           (datetime.datetime.now() + datetime.timedelta(days=loan_periode)).strftime('%Y-%m-%d'), loan_rules_id, 1)
    fetch_data(query, val)

    # Log peminjaman jika menggunakan SLiMS versi 9
    if slims_version == 9:
        query = """
            INSERT INTO system_log (log_type, id, log_location, sub_module, action, log_msg, log_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        val = ("system", user_id, "circulation", "Loan", "Add", "Gateway: Loan", datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        fetch_data(query, val)

    print(logtime(), "DB Closed")
    return resp

def handle_checkin(item_id, datetimeY, datetimeM, datetimeD):
    print(logtime(), datetimeY, datetimeM, datetimeD)

    # Check fines
    query = "SELECT loan_id FROM loan WHERE is_lent=1 AND is_return=0 AND TO_DAYS(due_date) < TO_DAYS(NOW()) AND item_code=%s"
    myresult = fetch_data(query, (item_id,))
    
    if myresult is None:
        return bytes("100NNY" + gettime() + "AO" + library_name + "|AB" + str(item_id) + "|AQ|AJ|AFGAGAL MENGHUBUNGKAN KE DATABASE" + "\r", 'utf-8')

    if len(myresult) != 0:
        return bytes("100NNY" + gettime() + "AO" + library_name + "|AB" + str(item_id) + "|AQ|AJ|AFANDA MENDAPAT DENDA, SILAHKAN KE SIRKULASI" + "\r", 'utf-8')

    # Check book
    query = "SELECT biblio_id FROM item WHERE item_code=%s"
    myresult = fetch_data(query, (item_id,))
    
    if myresult is None or len(myresult) == 0:
        return bytes("100NNY" + gettime() + "AO" + library_name + "|AB" + str(item_id) + "|AQ|AJ|AFBUKU TIDAK DITEMUKAN" + "\r", 'utf-8')

    # Get title
    biblio_id = myresult[0][0]
    query = "SELECT title FROM biblio WHERE biblio_id=%s"
    myresult = fetch_data(query, (biblio_id,))
    
    if myresult is None or len(myresult) == 0:
        return bytes("100NNY" + gettime() + "AO" + library_name + "|AB" + str(item_id) + "|AQ|AJ|AFBUKU TIDAK DITEMUKAN" + "\r", 'utf-8')

    title = myresult[0][0]

    # Check if the book is loaned
    query = "SELECT loan_id FROM loan WHERE item_code=%s AND is_lent=1 AND is_return=0 ORDER BY loan_id"
    myresult = fetch_data(query, (item_id,))
    
    if myresult is None:
        return bytes("100NNY" + gettime() + "AO" + library_name + "|AB" + str(item_id) + "|AQ|AJ|AFGAGAL MENGHUBUNGKAN KE DATABASE" + "\r", 'utf-8')

    if len(myresult) == 0:
        return bytes("100NNN" + gettime() + "AO" + library_name + "|AB" + str(item_id) + "|AQ|AJ" + title + "|AFBUKU BELUM DIPINJAM" + "\r", 'utf-8')

    # Update to loan
    query = "UPDATE loan SET is_return=%s, return_date=%s WHERE loan_id=%s"
    params = ("1", datetimeY + "-" + datetimeM + "-" + datetimeD, myresult[-1][0])
    
    db = connect_db()
    if db is None:
        return bytes("100NNY" + gettime() + "AO" + library_name + "|AB" + str(item_id) + "|AQ|AJ|AFGAGAL MENGHUBUNGKAN KE DATABASE" + "\r", 'utf-8')

    cursor = db.cursor()
    try:
        cursor.execute(query, params)
        db.commit()
        print(logtime(), cursor.rowcount, "record updated.")
        print(logtime(), cursor._warnings)
    except mysql.connector.Error as err:
        logging.error(f"{logtime()} DB Update Error: {err}")
        return bytes("100NNY" + gettime() + "AO" + library_name + "|AB" + str(item_id) + "|AQ|AJ|AFGAGAL MENGHUBUNGKAN KE DATABASE" + "\r", 'utf-8')
    finally:
        cursor.close()
        db.close()
        print(logtime(), "DB Closed")

    return bytes("101YNN" + gettime() + "AO" + library_name + "|AB" + str(item_id) + "|AQ|AJ" + title + "|AFBUKU BERHASIL DIKEMBALIKAN" + "\r", 'utf-8')

def handle_renewal(user_id, item_id):
    # Check if this item is being reserved by another member
    query = "SELECT l.item_code FROM reserve AS rs INNER JOIN loan AS l ON rs.item_code = l.item_code WHERE l.item_code = %s AND l.member_id != %s"
    reserved_result = fetch_data(query, (item_id, user_id))

    if reserved_result and len(reserved_result) > 0:
        return bytes("300NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AB" + str(item_id) + "|AJ|AFITEM DITAHAN OLEH ANGGOTA LAIN" + "\r", 'utf-8')

    # Check loan status
    query = "SELECT loan_id, due_date, renewed FROM loan WHERE is_lent = 1 AND is_return = 0 AND item_code = %s AND member_id = %s"
    loan_result = fetch_data(query, (item_id, user_id))

    if not loan_result or len(loan_result) == 0:
        return bytes("300NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AB" + str(item_id) + "|AJ|AFBUKU TIDAK DIPINJAM" + "\r", 'utf-8')

    loan_id, due_date, renewed = loan_result[0]

    # Check if item has already been renewed
    if renewed >= 1:
        return bytes("300NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AB" + str(item_id) + "|AJ|AFITEM SUDAH DIPERPANJANG SEBELUMNYA, TIDAK BISA DIPERPANJANG LAGI" + "\r", 'utf-8')

    # Get loan rules for this loan
    query = "SELECT loan_periode FROM mst_loan_rules WHERE loan_rules_id = (SELECT loan_rules_id FROM loan WHERE loan_id = %s)"
    loan_rules_result = fetch_data(query, (loan_id,))

    if not loan_rules_result or len(loan_rules_result) == 0:
        return bytes("300NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AB" + str(item_id) + "|AJ|AFLOAN RULES NOT FOUND" + "\r", 'utf-8')

    loan_periode = loan_rules_result[0][0]

    # Calculate new due date
    new_due_date = due_date + datetime.timedelta(days=loan_periode)

    # Get member expiry date
    query = "SELECT expire_date FROM member WHERE member_id = %s"
    expire_result = fetch_data(query, (user_id,))

    if not expire_result or len(expire_result) == 0:
        return bytes("300NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AB" + str(item_id) + "|AJ|AFMEMBER EXPIRY DATE NOT FOUND" + "\r", 'utf-8')

    expiry_date = expire_result[0][0]

    # Check if new due date exceeds member expiry date
    if new_due_date > expiry_date:
        new_due_date = expiry_date

    # Update loan with new due date and increment renewal count
    query = """
        UPDATE loan 
        SET renewed = renewed + 1, due_date = %s, is_return = 0 
        WHERE loan_id = %s
    """
    db = connect_db()
    if db is None:
        return bytes("300NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AB" + str(item_id) + "|AJ|AFGAGAL MENGHUBUNGKAN KE DATABASE" + "\r", 'utf-8')

    cursor = db.cursor()
    try:
        cursor.execute(query, (new_due_date.strftime('%Y-%m-%d'), loan_id))
        db.commit()
        print(logtime(), cursor.rowcount, "record updated.")
        print(logtime(), cursor._warnings)
    except mysql.connector.Error as err:
        logging.error(f"{logtime()} DB Update Error: {err}")
        return bytes("300NNN" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AB" + str(item_id) + "|AJ|AFGAGAL MENGHUBUNGKAN KE DATABASE" + "\r", 'utf-8')
    finally:
        cursor.close()
        db.close()
        print(logtime(), "DB Closed")

    return bytes("121YNY" + gettime() + "AO" + library_name + "|AA" + str(user_id) + "|AB" + str(item_id) + "|AJ|AFLOAN RENEWED SUCCESSFULLY" + "\r", 'utf-8')

def handle_patron_information(user_id):
    query = "SELECT member_name, expire_date FROM member WHERE member_id=%s"
    result = fetch_data(query, (user_id,))
    if not result:
        return bytes("64              001"+gettime()+(" "*24)+"AO"+library_name+"|BLN|AFANGGOTA TIDAK ADA"+"\r", "utf-8")

    name, expdate = result[0]
    if datetime.datetime.date(datetime.datetime.now()) > expdate:
        return bytes("64              001"+gettime()+(" "*24)+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANGGOTA TIDAK AKTIF"+"\r", "utf-8")

    query = "SELECT loan_id FROM loan WHERE is_lent=1 AND is_return=0 AND TO_DAYS(due_date) < TO_DAYS(NOW()) AND member_id=%s"
    overdue_loans = fetch_data(query, (user_id,))
    if overdue_loans:
        return bytes("64              001"+gettime()+(" "*24)+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+"|BLN|AFANDA DIKENAKAN DENDA, SILAHKAN HUBUNGI MEJA SIRKULASI"+"\r", "utf-8")

    query = "SELECT item_code FROM loan WHERE member_id=%s AND is_lent=1 AND is_return=0 ORDER BY loan_id"
    loan_result = fetch_data(query, (user_id,))
    loan_count = len(loan_result)
    summary = "Y" if loan_count > 0 else " "
    charged_item = "".join(f"|AU{id[0]}" for id in loan_result)

    return bytes("64  "+summary+"           001"+gettime()+(" "*8)+"   "+str(loan_count)+(" "*12)+"AO"+library_name+"|AA"+str(user_id)+"|AE"+name+charged_item+"|BLY"+"\r", "utf-8")

def handle_client(conn,addr):
    with conn:
        print(logtime(), f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            string = data.decode('utf-8')
            print(logtime(), string)
            if not data:
                break

            resp = bytes("", "utf-8")
            title = ""
            item_id = ""
            user_id = ""
            # SC registration
            if string[0:2] == "99":
                print(logtime(),"SC registration")
                resp = handle_sc_registration()
            # item information
            elif string[0:2] == "09":
                print(logtime(),"Checkin")
                item_id = string.split("AB")[1].split("|")[0]
                datetimeY = string[3:7]
                datetimeM = string[7:9]
                datetimeD = string[9:11]
                resp = handle_checkin(item_id,datetimeY,datetimeM,datetimeD)
                print(logtime(),"SIP RESPONSE : ",resp)
            elif string[0:2] == "11":
                user_id = string.split("AA")[1].split("|")[0]
                item_id = string.split("AB")[1].split("|")[0]
                resp = handle_checkout(user_id, item_id)
                print(logtime(),"SIP RESPONSE : ",resp)
            elif string[0:2] == "17":
                print(logtime(),"Item Information")
                item_id = string.split("AB")[1].split("|")[0]
                resp = handle_item_information(item_id)
                print(logtime(),"SIP RESPONSE : ",resp)
            elif string[0:2] == "23":
                print(logtime(),"Patron Status")
                user_id = string.split("AA")[1].split("|")[0]
                resp = handle_patron_status(user_id)
                print(logtime(),"SIP RESPONSE : ",resp)
            elif string[0:2] == "29":
                print(logtime(),"Item Renewal")
                user_id = string.split("AA")[1].split("|")[0]
                item_id = string.split("AB")[1].split("|")[0]
                resp = handle_renewal(user_id,item_id)
                print(logtime(),"SIP RESPONSE : ",resp)                
            elif string[0:2] == "35":
                print(logtime(),"Patron End Session")
                user_id = string.split("AA")[1].split("|")[0]
                resp = bytes("36Y"+gettime()+"|AO"+library_name+"|AA"+str(user_id)+"\r", 'utf-8')
                print(logtime(),"SIP RESPONSE : ",resp)
            elif string[0:2] == "63":
                print(logtime(),"Patron Information")
                user_id = string.split("AA")[1].split("|")[0]
                resp =  handle_patron_information(user_id)
                print(logtime(),"SIP RESPONSE : ",resp)
            conn.sendall(resp)

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print("WELCOME SIP2 SLIMS ")
        print(logtime(), "Server is ready to connect")
        while True:
            conn, addr = s.accept()
            handle_client(conn,addr)

if __name__ == "__main__":
    start_server()
