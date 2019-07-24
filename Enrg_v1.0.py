"""
Утилита для мониторинга энергопотребления GPU
Разработчик А.Фомичев
03.03.2018
"""
from sys import argv
from os import path as os_path, makedirs, listdir
from subprocess import call, Popen, PIPE, TimeoutExpired, getoutput
from time import sleep, strftime, time
from tkinter import *
from threading import Thread, activeCount
from re import findall

try:
    from colorama import init, Fore
except ImportError:
    call("python -m pip install colorama")
    try:
        from colorama import init, Fore
    except ImportError:
        pass

doc = """
v0.1 Alpha
Реализован базовый функционал.
Реализован запуск с параметрами:
 <-f> частота опроса, в сек.
 <-c> количество опрашиваемых GPU

v0.2.1 Beta
Реализован многопоточный мониторинг.
Реализованы статусы: N/A - адаптер не доступен. N/R - адаптер не отвечает.

v1.0 Release
Реализованы:
    --Графическое управление утилитой.
    --Автоматическое обнаружение доступных GPU.
    --Параметр <-c> больше не поддерживается(за ненадобностью).
    --Добавлен параметр <-a>, отвечающий за автозапуск мониторинга при запуске утилиты. 
        <-a> может принимать одно из двух значений: <yes> / <no> (<no> - по умолчанию).
        (пример: -a yes)
    --Добавлен параметр <-g>, описывающий какие GPU будут помечены как активные при запуске.
        <-g> - список номеров GPU (начиная с нулевого номера), разделенных запятой БЕЗ пробелов.
        (пример: -g 0,2,5,3)
    --Добавлена возможность создания CSV-файлов из лог-файлов. 
      
"""


def main():
    global flag, flag_p, c, f, path

    init(autoreset=True)

    file_name = path_logs + "\\logs_%s.txt" % strftime('%b_%d_%Y')
    date = strftime('%d')
    logs = open(file_name, 'a')

    print("\n" + Fore.GREEN + 'GPU Watt meter v0.2.1 by A.Fomichev. Log files in ' + path_logs + "\n")
    print("\n" + doc + "\n")

    while True:
        cnt = [i for i in c]
        ln = len(cnt)
        freq = f
        flag_l = flag
        flag_p_l = flag_p
        threads = [None for i in cnt]
        if flag_l and (1 in cnt):
            if not flag_p_l:
                print("Monitoring started! >%s<" % strftime('%X'))
                logs.write("\n\nMONITORING STARTED! >%s<\n" % strftime('%X'))
                flag_p = 1
            if strftime('%d') != date[1]:
                logs.close()
                date = strftime('%d')
                logs_file_name = path_logs + "\\logs_%s.txt" % strftime('%b_%d_%Y')
                logs = open(logs_file_name, 'a')
            OutPut = [Fore.RED + "N/R" for j in range(ln)]
            sleep(freq - 0.05 * ln)
            for i in range(ln):
                if cnt[i]:
                    threads[i] = Popen("nvidia-smi -i %d --format=csv,noheader --query-gpu=power.draw" % i, shell=True, stdout=PIPE)
                    try:
                        OutPut[i] = float(threads[i].communicate(timeout=0.1)[0][:-4])
                    except TimeoutExpired:
                        threads[i].kill()
                    except ValueError:
                        threads[i].kill()
                        OutPut[i] = "N/A"
            logs.write(strftime('%d/%m/%y %X') + ':%s>>>' % str((time() % 1) // 0.01)[:-2].rjust(2,'0'))
            for i in range(ln):
                if cnt[i]:
                    gpu_n = "GPU%d: " % i
                    watt = str(OutPut[i])
                    logs.write(" " + gpu_n + watt.ljust(6, ' ') + ' ')
                    print(Fore.CYAN + gpu_n + Fore.GREEN + watt.ljust(6, ' '), end=' ')
            logs.write('\n')
            print()
        elif flag_p_l:
            print("Monitoring stopped! >%s<\n" % strftime('%X'))
            flag_p = 0


if __name__ == "__main__":
    def monitoring(clk=0, state_to="another"):
        global flag, flag_p, mon_start
        flag_p = flag
        if state_to == "off":
            flag = 0
        elif state_to == "on":
            flag = 1
        elif state_to == "another":
            flag ^= 1
        if clk:
            mon_start["text"] = "Stop" if mon_start["text"] == "Start" else "Start"

    def to_csv(file_name, sep=";"):
        global logs_csv, path
        file = open(path_logs + "\\" + logs_csv[file_name], "r")
        r = file.read()
        file.close()
        head = ["Time"]
        for i in range(10):
            if re.search("U%d" % i, r) is not None:
                head.append("GPU %d" % i)
        r = re.sub('MONITORING STARTED! >.+<\n', '', r)
        r = re.sub('[0-9]+/[0-9]+/[0-9]+ ', '', r)
        r = re.sub(' +\n', '\n', r)
        r = re.sub('GPU[0-9]:', '', r)
        r = re.sub(' +', sep, r)
        r = re.sub('>>>', '', r)
        r = re.sub('\n\n\n\n', '\n', r)
        r = re.sub('\n\n\n', '\n', r)
        r = re.sub('\n\n', '\n', r)
        r = re.sub('\A', '%s' % sep.join(head), r)
        r = re.sub('\.', ',', r)
        if "CSV_logs" not in listdir(path=path):
            print(listdir(path=path))
            makedirs(path + "\\CSV_logs",)
        file = open(path + '\\CSV_logs\\csv_' + logs_csv[file_name], "w")
        file.write(r)
        file.close()

    def frq_change(event):
        global f
        try:
            f = float(frq.get())
            if f < 0.5:
                print(Fore.RED + "Too small <frequency> value: <%s>. Frequency was set to a minimum: <0.5>." % frq.get())
                f = 0.5
            frq.delete(0, END)
            frq.insert(0, str(f))
        except ValueError:
            print(Fore.RED + "Bad <frequency> value: <%s>. Frequency was set to default: <1>." % frq.get())
            f = 1
            frq.delete(0, END)
            frq.insert(0, '1')

    def gpu_checked(i):
        c[i] ^= 1
        if 1 not in c:
            mon_start["state"] = DISABLED
            mon_start["text"] = "Start"
            monitoring(state_to="off")
        else:
            mon_start["state"] = NORMAL

    def list_logs(event):
        global csv_op, logs_csv
        if not csv_op:
            if len(logs_csv) < 16:
                make_csv["height"] = len(logs_csv)
            else:
                make_csv["height"] = 16
            make_csv.update()
            make_csv.delete(0, END)
            for i in range(len(logs_csv)):
                make_csv.insert(i, logs_csv[i])
            csv_op = 1

    def refresh(event):
        global csv_op, logs_csv
        csv_op = 0
        make_csv["height"] = 1

    def sel(event):
        global cur_selection
        try:
            cur_selection = int(make_csv.curselection()[0])
        except IndexError:
            pass
        if cur_selection is not None:
            make_csv_btn["state"] = NORMAL


    init(autoreset=True)

    path = '\\'.join(os_path._getfullpathname(__file__).split('\\')[:-1])
    path_logs = path + '\\Logs' #!!!
    if not os_path.exists(path_logs):
        makedirs(path_logs)

    gpu_info = findall('(GPU.*) \(', getoutput("nvidia-smi -L"))
    ln_gpu_info = len(gpu_info)
    gpu_on = [None for i in range(ln_gpu_info)]
    c = [0 for i in gpu_on]
    f = 1
    a = 'no'
    csv_op = 0
    cur_selection = None
    logs_csv = listdir(path_logs)
    for i in range(len(argv)):
        if argv[i] == '-f':
            try:
                f = float(argv[i + 1])
            except ValueError:
                print(Fore.RED + """Bad <frequency> value: <%s>. Frequency was set to default: <1>.""" % argv[i+1])
            except IndexError:
                pass
        elif argv[i] == '-a':
            try:
                if argv[i+1] == 'yes' or argv[i+1] == 'no':
                    a = argv[i+1]
            except IndexError:
                pass
        elif argv[i] == '-g':
            try:
                cc = list(map(int, argv[i+1].split(',')))
                valid_list = 1
                for el in cc:
                    if not (0 <= el < ln_gpu_info):
                        valid_list = 0
                        continue
                    else:
                        c[el] = 1
            except (IndexError, ValueError):
                pass

    flag_p = 0
    flag = 0

    root = Tk()
    root.geometry("410x350")
    root.resizable(False, False)

    r_canv = Canvas(root, width=411, height=351, bg="gray97")
    r_canv.bind("<Button-1>", refresh)

    mon_start = Button(r_canv, width=10, height=1, command=lambda clk=1: monitoring(clk), text="Start")
    if 1 not in c:
        mon_start["state"] = DISABLED
    elif a == 'yes':
        monitoring(clk=1,state_to="on")

    Thread(target=main).start()

    frq = Entry(width=10, text="1", justify="right")
    frq.insert(0,f)
    for i in range(ln_gpu_info):
        gpu_on[i] = Checkbutton(r_canv, anchor=NW, text=gpu_info[i], bg="gray97", command=lambda ind=i: gpu_checked(ind))
        if c[i]:
            gpu_on[i].select()
        gpu_on[i].place(x=5, y=25+i*25)

    separator = StringVar()

    make_csv = Listbox(r_canv, height=1, borderwidth=0)
    make_csv.bind("<Button-1>", list_logs)
    make_csv.bind("<<ListboxSelect>>", sel)
    make_csv_btn = Button(r_canv, width=10, height=1, text="make", state=DISABLED, command=lambda: to_csv(cur_selection))

    r_canv.create_line(-1, 23, 450, 23, fill="gray80")
    r_canv.create_line(190, 0, 190, 350, fill="gray80")
    r_canv.create_line(-1, 50 + ln_gpu_info * 25, 190, 50 + ln_gpu_info * 25, fill="gray80")
    r_canv.create_line(410, 0, 410, 350, fill="gray80")
    r_canv.create_text(95, 12, text="Graphic cards:")
    r_canv.create_text(40, 65 + ln_gpu_info * 25, text="Frequency: ")
    r_canv.create_text(315, 12, text="Make CSV_log file:")
    r_canv.create_text(230, 37, text="Choose file: ")

    frq.bind("<Return>", frq_change)

    make_csv_btn.place(x=320,y=315)
    make_csv.place(x=270,y=28)
    r_canv.place(x=-1, y=-1)
    frq.place(x=80, y=55+ln_gpu_info*25)
    mon_start.place(x=100, y=315)
    root.mainloop()