import pyb, os
try:
    os.umount('/flash')
except Exception: 
    pass
print('Creating new filesystem')
os.VfsLfs1.mkfs(pyb.Flash(start=0))
os.mount(pyb.Flash(start=0), '/flash')
os.chdir('/flash')
f=open('main.py', 'w')
f.write('# main.py -- put your code here!\r\n')
f.close()
print(os.statvfs('/flash'))
print(os.listdir())
f=open('main.py')
print(f.read())
f.close()