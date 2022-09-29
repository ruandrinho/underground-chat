import tkinter as tk
import anyio
from tkinter import messagebox


class TkAppClosed(Exception):
    pass


def process_nickname_enter(input_field, events_queue):
    text = input_field.get()
    events_queue.put_nowait(text)
    input_field.delete(0, tk.END)


async def show_success(nickname):
    messagebox.showinfo('Вы успешно зарегистрированы', f'Хэш сохранён в файле {nickname}.token')
    root.destroy()
    raise TkAppClosed


async def update_tk(root_frame, interval=1 / 120):
    while True:
        root_frame.update()
        await anyio.sleep(interval)


async def draw(events_queue):
    global root
    root = tk.Tk()
    # root.protocol('WM_DELETE_WINDOW', root.destroy)

    root.title('Регистрация в чате Майнкрафтера')
    root.minsize(400, 0)
    root.resizable(False, False)

    root_frame = tk.Frame()
    root_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    nickname_label = tk.Label(root_frame, height=1, fg='grey', font='arial 10', anchor='w')
    nickname_label.grid(row=0, column=0)
    nickname_label['text'] = 'Имя пользователя'

    input_field = tk.Entry(root_frame, width=30)
    input_field.grid(row=1, column=0)

    input_field.bind("<Return>", lambda event: process_nickname_enter(input_field, events_queue))

    blank_label = tk.Label(root_frame, height=1, fg='grey', font='arial 10', anchor='w')
    blank_label.grid(row=2, column=0)

    send_button = tk.Button(root_frame)
    send_button["text"] = "Отправить"
    send_button["command"] = lambda: process_nickname_enter(input_field, events_queue)
    send_button.grid(row=3, column=0)

    async with anyio.create_task_group() as tg:
        tg.start_soon(update_tk, root_frame)
