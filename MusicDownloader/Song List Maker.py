import csv, os ,sys
os.chdir(sys.path[0])
print(sys.path[0])
File=open('SongList.csv', 'w', newline='')
Writer=csv.writer(File)
song=''
print("\n\n\n\n===SONG LIST MAKER===\n\nType 'exit' to save and exit\nFormat:' Artist Name - Song Name '\n\n")
while(song!='exit'):
    if(song):
        Writer.writerow([str(song)])
    song=input("Enter a song name: ")
    

File.close()

File=open('SongList.csv', 'r')
FileList=csv.reader(File)
for Row in FileList:
    print(Row[0])
    
