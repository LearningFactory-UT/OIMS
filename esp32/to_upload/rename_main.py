import os

def rename_main():
    if 'main.py' in os.listdir():
        os.rename('main.py', 'main_.py')
        print('Renamed main.py to main_.py')
    elif 'main_.py' in os.listdir():
        os.rename('main_.py', 'main.py')
        print('Renamed main_.py to main.py')
    else:
        print('Neither main.py nor main_.py found.')

rename_main()
