# SIP2-API
SIP2 Gateway for API Communication
# How To Use
- Install python3 (minimal 3.9 or above) in LMS server
- Run the Python Code

# Reference Standard Interchange Protocol : 
https://developers.exlibrisgroup.com/wp-content/uploads/2020/01/3M-Standard-Interchange-Protocol-Version-2.00.pdf

# Bibliotheca Selfcheck 1000 Settings (Indonesia) : 
https://tlkm.id/R8oaN2

# Kebutuhan Endpoint 

Endpoint 1 : get book information
- Method : GET
request : judul buku, status buku (dipinjam/available), due_date (batas pengembalian buku)


Endpoint 2 : get member information
- Method : GET
request : nama, denda, masa aktif kartu anggota, kode barcode buku yang dipinjam

Endpoint 3 : proses peminjaman
- Method : POST
input json : NIM, kode barcode buku yang dipinjam

Endpoint 4 : proses pengembalian
- Method : PUT
input json : kode barcode buku yang dipinjam
