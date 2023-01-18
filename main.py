import json
import os
import shutil
import subprocess
import tkinter
import winreg
from pathlib import Path
from tkinter import Frame, Tk, NW, DISABLED, NORMAL, Toplevel, CENTER, messagebox
from tkinter.ttk import Combobox, Label, Entry, Button


def close_egs():
    try:
        return subprocess.check_call("taskkill /f /im EpicGamesLauncher.exe", shell=True)
    except subprocess.CalledProcessError:
        return 1


def get_egs_manifest_directory():
    target_key = r"\SOFTWARE\Epic Games\EOS"

    users = winreg.QueryInfoKey(winreg.HKEY_USERS)
    for i in range(0, users[0]):
        user = winreg.EnumKey(winreg.HKEY_USERS, i)
        try:
            registry = winreg.OpenKey(winreg.HKEY_USERS, user + target_key, 0, winreg.KEY_READ)
            data_tuple = winreg.QueryValueEx(registry, "ModSdkMetadataDir")

            if data_tuple and data_tuple[0] != "":
                return os.path.normpath(data_tuple[0])

        except FileNotFoundError:
            continue
        except PermissionError:
            continue

    return None


def get_egs_items():
    manifest_directory = get_egs_manifest_directory()

    items = []
    for item in os.listdir(manifest_directory):
        if item.endswith(".item"):
            items.append(os.path.join(manifest_directory, item))

    return items


def get_unreal_items():
    ue_items = {}
    unreal_binary_names = ("UnrealEditor", "UE4Editor")
    for item in get_egs_items():
        with open(item, "r") as f:
            data = json.load(f)

            if any(str in data["LaunchExecutable"] for str in unreal_binary_names):
                ue_items[item] = data

    return ue_items


def get_unreal_manifest(ue_item: dict):
    manifest_location = os.path.normpath(ue_item["ManifestLocation"])
    installation_guid = ue_item["InstallationGuid"] + ".mancpn"

    return os.path.join(manifest_location, installation_guid)


def get_unreal_version(ue_item: dict):
    return ue_item["AppName"][3:]


def create_backup(path: str, backup_root_dir: str):
    backup_dir = os.path.join(backup_root_dir, Path(path).stem)
    backup_path = os.path.join(backup_dir, os.path.basename(path))

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    shutil.copy(path, backup_path)


def restore_backup(path: str, backup_dir: str):
    backup_path = os.path.join(backup_dir, Path(path).stem, os.path.basename(path))
    shutil.copy(backup_path, path)


def change_item_version(path: str, ue_item: dict, version: str):
    original_version = get_unreal_version(ue_item)
    ue_item["AppName"] = "UE_" + version
    ue_item["MainGameAppName"] = "UE_" + version
    # Make it clear what version has what installed
    ue_item["AppVersionString"] = ue_item["AppVersionString"].replace(original_version, version)

    with open(path, "w") as f:
        json.dump(ue_item, f, indent=4)


def change_manifest_version(ue_item: dict, version: str):
    manifest = get_unreal_manifest(ue_item)
    with open(manifest, "r") as f:
        data = json.load(f)

    data["AppName"] = "UE_" + version
    with open(manifest, "w") as f:
        json.dump(data, f, indent=4)


def change_version(path: str, ue_item: dict, version: str):
    change_item_version(path, ue_item, version)
    change_manifest_version(ue_item, version)


def show_egs_closing_message():
    message_window = Toplevel()
    message_window.geometry("250x100")
    message_window.title("")
    message_window.after(5000, message_window.destroy)

    frame = Frame(message_window, width=250, height=100)
    frame.grid(row=0, column=0, sticky="NW")

    message_label = tkinter.Label(frame, text="Closing Epic Games Launcher... Please wait.")
    message_label.place(relx=0.5, rely=0.5, anchor=CENTER)

    message_window.grab_set()

def main():
    backup_dir = os.path.join(os.path.dirname(__file__), "EpicGamesBackup")
    unreal_items = get_unreal_items()

    unreal_versions = [get_unreal_version(data) for path, data in unreal_items.items()]

    root = Tk()
    root.geometry("250x100")
    root.title("")
    root.wm_resizable(False, False)
    frame = Frame(root, bd=8)
    frame.pack(fill="both")

    # Top
    top_frame = Frame(frame, padx=4, pady=4)
    top_frame.grid(row=0, column=0, sticky=NW)

    label = Label(top_frame, text="UE version")
    label.grid(row=0, column=0, sticky=NW)

    unreal_combobox = Combobox(top_frame, values=unreal_versions)
    unreal_combobox.current(0)
    unreal_combobox.grid(row=0, column=1, sticky=NW, padx=8)

    # Middle
    middle_frame = Frame(frame, padx=4, pady=4)
    middle_frame.grid(row=1, column=0, sticky=NW)

    label = Label(middle_frame, text="New UE version")
    label.grid(row=0, column=0, sticky=NW)

    version_entry = Entry(middle_frame)
    version_entry.insert(0, "5.0")
    version_entry.grid(row=0, column=1, sticky=NW, padx=8)

    # Bottom
    bottom_frame = Frame(frame, padx=4, pady=4)
    bottom_frame.grid(row=2, column=0, sticky=NW)

    restore_needed = False

    def on_change_version():
        nonlocal restore_needed
        close_egs()

        unreal_combobox["state"] = DISABLED
        version_entry["state"] = DISABLED
        button_change["state"] = DISABLED
        button_engine["state"] = DISABLED
        button_restore["state"] = NORMAL
        restore_needed = True

        for path, data in unreal_items.items():
            create_backup(path, backup_dir)
            create_backup(get_unreal_manifest(data), backup_dir)

        unreal_version = unreal_combobox.get()
        version = version_entry.get()

        for path, data in unreal_items.items():
            if get_unreal_version(data) == unreal_version:
                change_version(path, data, version)

    def on_restore_version():
        nonlocal restore_needed
        close_egs()

        unreal_combobox["state"] = NORMAL
        version_entry["state"] = NORMAL
        button_change["state"] = NORMAL
        button_engine["state"] = NORMAL
        button_restore["state"] = DISABLED
        restore_needed = False

        for path, data in unreal_items.items():
            unreal_version = version_entry.get()

            if get_unreal_version(data) == unreal_version:
                restore_backup(path, backup_dir)
                restore_backup(get_unreal_manifest(data), backup_dir)

                with open(path, "r") as f:
                    unreal_items[path] = json.load(f)

    def on_open_engine_dir():
        unreal_version = unreal_combobox.get()
        for path, data in unreal_items.items():
            if get_unreal_version(data) == unreal_version:
                plugins_location = os.path.join(data["InstallLocation"], "Engine", "Plugins")
                marketplace_location = os.path.join(plugins_location, "Marketplace")

                if os.path.exists(marketplace_location):
                    os.startfile(marketplace_location)
                else:
                    messagebox.showerror("Error", f"Directory doesn't exist: {marketplace_location}")
                    if os.path.exists(plugins_location):
                        os.startfile(plugins_location)

    button_change = Button(bottom_frame, text="Change", command=on_change_version)
    button_change.grid(row=0, column=0, sticky=NW)

    button_restore = Button(bottom_frame, text="Restore", command=on_restore_version, state=DISABLED)
    button_restore.grid(row=0, column=1, sticky=NW)

    button_engine = Button(bottom_frame, text="Open", command=on_open_engine_dir)
    button_engine.grid(row=0, column=3, sticky=NW)

    def on_close():
        nonlocal restore_needed
        if restore_needed:
            on_restore_version()

        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == '__main__':
    main()
