import os
import shutil
import google.generativeai as genai
import re
import subprocess
import platform
import ctypes
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)  # Fixed underscores
CORS(app)  # Enable CORS for all routes

GENAI_API_KEY = ""
genai.configure(api_key=GENAI_API_KEY)

model = genai.GenerativeModel("gemini-1.5-pro-latest")

def get_task_from_gemini(command):
    """Passes user speech text to Gemini for classification."""
    prompt = f"""
    Analyze the following command and check if it is related to file/folder operations, volume control, or brightness control:
    
    Examples:
    - Create a file example.txt
    - Delete file example.txt
    - Rename file from old.txt to new.txt
    - Move file from source.txt to destination.txt
    - Create a folder Projects
    - Delete folder Projects
    - Rename folder from Projects to MyWork
    - Move folder from MyWork to Documents
    - Go to C drive and create a file example.txt
    - Go to C:\\Users\\Documents and create a folder Projects
    - Navigate to D:\\Work and delete file report.txt
    - Create a file report.txt in C:\\Users\\Documents
    - Create a folder Temp in D:\\Projects
    
    # New volume control examples:
    - Increase volume
    - Decrease volume
    - Set volume to 50 percent
    - Mute volume
    - Unmute volume
    - Set volume to maximum
    
    # New brightness control examples:
    - Increase brightness
    - Decrease brightness
    - Set brightness to 50 percent
    - Set brightness to maximum
    - Set brightness to minimum
    
    User command: "{command}"
    
    If the command is related to file/folder operations, return a formatted command that clearly specifies:
    1. The operation type (create/delete/rename/move/navigate)
    2. The object type (file/folder)
    3. The path and name information
    
    Format your response for file/folder operations like:
    - "CREATE FILE C:\\path\\to\\filename.txt"
    - "DELETE FOLDER D:\\path\\to\\folder"
    - "RENAME FILE FROM C:\\path\\old.txt TO C:\\path\\new.txt"
    - "MOVE FOLDER FROM D:\\source TO E:\\destination"
    - "NAVIGATE TO C:\\path\\to\\location"
    
    If the command is related to volume control, return a formatted command that clearly specifies:
    1. The operation type (VOLUME)
    2. The action (INCREASE/DECREASE/SET/MUTE/UNMUTE)
    3. The level (if applicable, as a percentage from 0-100)
    
    Format your response for volume control like:
    - "VOLUME INCREASE"
    - "VOLUME DECREASE"
    - "VOLUME SET 50"
    - "VOLUME MUTE"
    - "VOLUME UNMUTE"
    - "VOLUME MAXIMUM"
    
    If the command is related to brightness control, return a formatted command that clearly specifies:
    1. The operation type (BRIGHTNESS)
    2. The action (INCREASE/DECREASE/SET)
    3. The level (if applicable, as a percentage from 0-100)
    
    Format your response for brightness control like:
    - "BRIGHTNESS INCREASE"
    - "BRIGHTNESS DECREASE"
    - "BRIGHTNESS SET 50"
    - "BRIGHTNESS MAXIMUM"
    - "BRIGHTNESS MINIMUM"
    
    If it is not related to file/folder operations, volume control, or brightness control, return "UNKNOWN".
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def control_volume(action, level=None):
    """Controls system volume based on the specified action and level."""
    try:
        system = platform.system()
        
        if system == "Windows":
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)  # Added underscores
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            if action == "INCREASE":
                current_vol = volume.GetMasterVolumeLevelScalar()
                new_vol = min(1.0, current_vol + 0.1)
                volume.SetMasterVolumeLevelScalar(new_vol, None)
                return f"🔊 Volume increased to {int(new_vol * 100)}%"
                
            elif action == "DECREASE":
                current_vol = volume.GetMasterVolumeLevelScalar()
                new_vol = max(0.0, current_vol - 0.1)
                volume.SetMasterVolumeLevelScalar(new_vol, None)
                return f"🔉 Volume decreased to {int(new_vol * 100)}%"
                
            elif action == "SET" and level is not None:
                level_float = float(level) / 100.0
                volume.SetMasterVolumeLevelScalar(level_float, None)
                return f"🔊 Volume set to {level}%"
                
            elif action == "MUTE":
                volume.SetMute(1, None)
                return "🔇 Volume muted"
                
            elif action == "UNMUTE":
                volume.SetMute(0, None)
                return "🔊 Volume unmuted"
                
            elif action == "MAXIMUM":
                volume.SetMasterVolumeLevelScalar(1.0, None)
                return "🔊 Volume set to maximum (100%)"
                
        elif system == "Darwin":  # macOS
            if action == "INCREASE":
                os.system("osascript -e 'set volume output volume (output volume of (get volume settings) + 10)'")
                return "🔊 Volume increased"
                
            elif action == "DECREASE":
                os.system("osascript -e 'set volume output volume (output volume of (get volume settings) - 10)'")
                return "🔉 Volume decreased"
                
            elif action == "SET" and level is not None:
                os.system(f"osascript -e 'set volume output volume {level}'")
                return f"🔊 Volume set to {level}%"
                
            elif action == "MUTE":
                os.system("osascript -e 'set volume with output muted'")
                return "🔇 Volume muted"
                
            elif action == "UNMUTE":
                os.system("osascript -e 'set volume without output muted'")
                return "🔊 Volume unmuted"
                
            elif action == "MAXIMUM":
                os.system("osascript -e 'set volume output volume 100'")
                return "🔊 Volume set to maximum (100%)"
                
        elif system == "Linux":
            if action == "INCREASE":
                os.system("amixer -D pulse sset Master 10%+")
                return "🔊 Volume increased"
                
            elif action == "DECREASE":
                os.system("amixer -D pulse sset Master 10%-")
                return "🔉 Volume decreased"
                
            elif action == "SET" and level is not None:
                os.system(f"amixer -D pulse sset Master {level}%")
                return f"🔊 Volume set to {level}%"
                
            elif action == "MUTE":
                os.system("amixer -D pulse sset Master mute")
                return "🔇 Volume muted"
                
            elif action == "UNMUTE":
                os.system("amixer -D pulse sset Master unmute")
                return "🔊 Volume unmuted"
                
            elif action == "MAXIMUM":
                os.system("amixer -D pulse sset Master 100%")
                return "🔊 Volume set to maximum (100%)"
                
        return "⚠ Volume control not implemented for your operating system."
        
    except Exception as e:
        return f"⚠ Error controlling volume: {e}"

def control_brightness(action, level=None):
    """Controls system brightness based on the specified action and level."""
    try:
        system = platform.system()
        
        if system == "Windows":
            try:
                import wmi
                wmi_instance = wmi.WMI(namespace='root\\WMI')
                monitors = wmi_instance.WmiMonitorBrightness()
                
                if len(monitors) > 0:
                    brightness_methods = wmi_instance.WmiMonitorBrightnessMethods()[0]
                    current_brightness = monitors[0].CurrentBrightness
                    
                    if action == "INCREASE":
                        new_brightness = min(100, current_brightness + 10)
                        brightness_methods.WmiSetBrightness(new_brightness, 0)
                        return f"☀ Brightness increased to {new_brightness}%"
                        
                    elif action == "DECREASE":
                        new_brightness = max(0, current_brightness - 10)
                        brightness_methods.WmiSetBrightness(new_brightness, 0)
                        return f"🔆 Brightness decreased to {new_brightness}%"
                        
                    elif action == "SET" and level is not None:
                        brightness_methods.WmiSetBrightness(int(level), 0)
                        return f"☀ Brightness set to {level}%"
                        
                    elif action == "MAXIMUM":
                        brightness_methods.WmiSetBrightness(100, 0)
                        return "☀ Brightness set to maximum (100%)"
                        
                    elif action == "MINIMUM":
                        brightness_methods.WmiSetBrightness(0, 0)
                        return "🔅 Brightness set to minimum (0%)"
                        
            except ImportError:
                # Fallback using PowerShell
                if action == "INCREASE":
                    subprocess.run(["powershell", "-command", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,10)"], 
                                 capture_output=True)
                    return "☀ Brightness increased"
                    
                elif action == "DECREASE":
                    subprocess.run(["powershell", "-command", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,-10)"], 
                                 capture_output=True)
                    return "🔆 Brightness decreased"
                    
                elif action == "SET" and level is not None:
                    subprocess.run(["powershell", "-command", f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"], 
                                 capture_output=True)
                    return f"☀ Brightness set to {level}%"
                    
                elif action == "MAXIMUM":
                    subprocess.run(["powershell", "-command", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,100)"], 
                                 capture_output=True)
                    return "☀ Brightness set to maximum (100%)"
                    
                elif action == "MINIMUM":
                    subprocess.run(["powershell", "-command", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,0)"], 
                                 capture_output=True)
                    return "🔅 Brightness set to minimum (0%)"
                
        elif system == "Darwin":  # macOS
            if action == "INCREASE":
                os.system("brightness -i 10")
                return "☀ Brightness increased"
                
            elif action == "DECREASE":
                os.system("brightness -d 10")
                return "🔆 Brightness decreased"
                
            elif action == "SET" and level is not None:
                level_float = float(level) / 100.0
                os.system(f"brightness {level_float}")
                return f"☀ Brightness set to {level}%"
                
            elif action == "MAXIMUM":
                os.system("brightness 1")
                return "☀ Brightness set to maximum (100%)"
                
            elif action == "MINIMUM":
                os.system("brightness 0")
                return "🔅 Brightness set to minimum (0%)"
                
        elif system == "Linux":
            try:
                # Find the first backlight device
                backlight_dir = "/sys/class/backlight/"
                devices = os.listdir(backlight_dir)
                
                if devices:
                    device = devices[0]
                    max_brightness_file = f"{backlight_dir}{device}/max_brightness"
                    brightness_file = f"{backlight_dir}{device}/brightness"
                    
                    with open(max_brightness_file, 'r') as f:
                        max_brightness = int(f.read().strip())
                        
                    with open(brightness_file, 'r') as f:
                        current_brightness = int(f.read().strip())
                        
                    current_percent = (current_brightness / max_brightness) * 100
                    
                    if action == "INCREASE":
                        new_percent = min(100, current_percent + 10)
                        new_brightness = int((new_percent / 100) * max_brightness)
                        with open(brightness_file, 'w') as f:
                            f.write(str(new_brightness))
                        return f"☀ Brightness increased to {int(new_percent)}%"
                        
                    elif action == "DECREASE":
                        new_percent = max(0, current_percent - 10)
                        new_brightness = int((new_percent / 100) * max_brightness)
                        with open(brightness_file, 'w') as f:
                            f.write(str(new_brightness))
                        return f"🔆 Brightness decreased to {int(new_percent)}%"
                        
                    elif action == "SET" and level is not None:
                        new_brightness = int((float(level) / 100) * max_brightness)
                        with open(brightness_file, 'w') as f:
                            f.write(str(new_brightness))
                        return f"☀ Brightness set to {level}%"
                        
                    elif action == "MAXIMUM":
                        with open(brightness_file, 'w') as f:
                            f.write(str(max_brightness))
                        return "☀ Brightness set to maximum (100%)"
                        
                    elif action == "MINIMUM":
                        with open(brightness_file, 'w') as f:
                            f.write("0")
                        return "🔅 Brightness set to minimum (0%)"
            except Exception as e:
                # Fallback for Linux using xbacklight
                if action == "INCREASE":
                    os.system("xbacklight -inc 10")
                    return "☀ Brightness increased"
                    
                elif action == "DECREASE":
                    os.system("xbacklight -dec 10")
                    return "🔆 Brightness decreased"
                    
                elif action == "SET" and level is not None:
                    os.system(f"xbacklight -set {level}")
                    return f"☀ Brightness set to {level}%"
                    
                elif action == "MAXIMUM":
                    os.system("xbacklight -set 100")
                    return "☀ Brightness set to maximum (100%)"
                    
                elif action == "MINIMUM":
                    os.system("xbacklight -set 0")
                    return "🔅 Brightness set to minimum (0%)"
                    
        return "⚠ Brightness control not implemented for your operating system."
        
    except Exception as e:
        return f"⚠ Error controlling brightness: {e}"

def interpret_command(command):
    """Analyzes the Gemini-processed command and performs operations."""
    try:
        command = command.strip()
        print(f"🔍 Processed Command: {command}")
        
        if command == "UNKNOWN":
            return "⚠ Command not recognized."

        parts = command.split()
        operation = parts[0].upper() if parts else ""
        
        # Handle volume control commands
        if operation == "VOLUME":
            if len(parts) >= 2:
                action = parts[1].upper()
                level = int(parts[2]) if len(parts) >= 3 else None
                return control_volume(action, level)
        
        # Handle brightness control commands
        elif operation == "BRIGHTNESS":
            if len(parts) >= 2:
                action = parts[1].upper()
                level = int(parts[2]) if len(parts) >= 3 else None
                return control_brightness(action, level)
        
        # Handle navigation commands
        elif operation == "NAVIGATE":
            location_index = command.upper().find("TO ")
            if location_index != -1:
                path = command[location_index + 3:].strip()
                if os.path.exists(path):
                    os.chdir(path)
                    return f"📂 Changed directory to {path}"
                else:
                    return f"⚠ Path does not exist: {path}"
        
        # Handle file/folder creation
        elif operation == "CREATE":
            if len(parts) >= 2 and parts[1].upper() == "FILE":
                filepath = " ".join(parts[2:])
                directory = os.path.dirname(filepath)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                open(filepath, 'w').close()
                return f"✅ File '{filepath}' created successfully."
            
            elif len(parts) >= 2 and parts[1].upper() == "FOLDER":
                folderpath = " ".join(parts[2:])
                os.makedirs(folderpath, exist_ok=True)
                return f"📁 Folder '{folderpath}' created successfully."
        
        # Handle file/folder deletion
        elif operation == "DELETE":
            if len(parts) >= 2 and parts[1].upper() == "FILE":
                filepath = " ".join(parts[2:])
                if os.path.exists(filepath):
                    os.remove(filepath)
                    return f"🗑 File '{filepath}' deleted successfully."
                else:
                    return f"⚠ File does not exist: {filepath}"
            
            elif len(parts) >= 2 and parts[1].upper() == "FOLDER":
                folderpath = " ".join(parts[2:])
                if os.path.exists(folderpath):
                    shutil.rmtree(folderpath)
                    return f"🗑 Folder '{folderpath}' deleted successfully."
                else:
                    return f"⚠ Folder does not exist: {folderpath}"
        
        # Handle file/folder renaming
        elif operation == "RENAME":
            if "FROM" in command.upper() and "TO" in command.upper():
                from_index = command.upper().find("FROM ")
                to_index = command.upper().find(" TO ")
                
                if from_index != -1 and to_index != -1:
                    old_path = command[from_index + 5:to_index].strip()
                    new_path = command[to_index + 4:].strip()
                    
                    if os.path.exists(old_path):
                        new_dir = os.path.dirname(new_path)
                        if new_dir and not os.path.exists(new_dir):
                            os.makedirs(new_dir, exist_ok=True)
                            
                        os.rename(old_path, new_path)
                        
                        if "FILE" in parts:
                            return f"🔄 File renamed from '{old_path}' to '{new_path}'."
                        else:
                            return f"🔄 Folder renamed from '{old_path}' to '{new_path}'."
                    else:
                        return f"⚠ Source path does not exist: {old_path}"
        
        # Handle file/folder moving
        elif operation == "MOVE":
            if "FROM" in command.upper() and "TO" in command.upper():
                from_index = command.upper().find("FROM ")
                to_index = command.upper().find(" TO ")
                
                if from_index != -1 and to_index != -1:
                    src_path = command[from_index + 5:to_index].strip()
                    dest_path = command[to_index + 4:].strip()
                    
                    if os.path.exists(src_path):
                        dest_dir = os.path.dirname(dest_path)
                        if dest_dir and not os.path.exists(dest_dir):
                            os.makedirs(dest_dir, exist_ok=True)
                            
                        shutil.move(src_path, dest_path)
                        
                        if "FILE" in parts:
                            return f"📂 File moved from '{src_path}' to '{dest_path}'."
                        else:
                            return f"📂 Folder moved from '{src_path}' to '{dest_path}'."
                    else:
                        return f"⚠ Source path does not exist: {src_path}"
        
        return "⚠ Command not recognized or incorrectly formatted."
    
    except Exception as e:
        return f"⚠ Error: {e}"

# Flask API endpoint to process commands
@app.route('/api/process-command', methods=['POST'])
def process_command():
    command = request.json.get('command', '')
    if not command:
        return jsonify({"response": "⚠ No command provided."})
    
    try:
        gemini_response = get_task_from_gemini(command)
        result = interpret_command(gemini_response)
        return jsonify({"response": result})
    except Exception as e:
        return jsonify({"response": f"⚠ Error: {str(e)}"})

# Flask API endpoint to provide help information
@app.route('/api/get-help', methods=['GET'])
def get_help():
    help_info = {
        "basic_commands": [
            "Create a file example.txt",
            "Delete file example.txt", 
            "Rename file from old.txt to new.txt",
            "Move file from source.txt to destination.txt",
            "Create a folder Projects",
            "Delete folder Projects",
            "Navigate to [path]"
        ],
        "advanced_commands": [
            "Increase volume",
            "Decrease volume",
            "Set volume to 50 percent",
            "Increase brightness",
            "Decrease brightness",
            "Set brightness to 70 percent",
            "Create a file report.txt in D:\\Work"
        ]
    }
    return jsonify(help_info)

if __name__ == "__main__":  # Fixed underscores
    app.run(host='0.0.0.0', port=5000, debug=True)