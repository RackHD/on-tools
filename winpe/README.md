# Editing the WINPE Operating System for windows installation


### Download Windows ADK (Assessment and Deployment Kit)
It is recommended that you use Windows ADK for windows 10
https://developer.microsoft.com/en-us/windows/hardware/windows-assessment-deployment-kit 

### Copy the winpe files
- Run the **Deployment and Imaging Tools Environment** application as administrator 
You can do so by going to the **Start** menu, choose **All Programs** → **Windows Kits** → **Windows ADK**→ **Deployment and Imaging Tools Environment**
- Copy the Windows PE files that you will be working with based on the hardware architecture that you are using. x86, amd64, or arm
for example ```copype amd64 C:\WinPE_amd64_PS```

### Add PowerShell to Windows PE
- create a script with the bellow commands. ```notepad addingPowershell.bat```

```
Dism /Mount-Image /ImageFile:"C:\WinPE_amd64_PS\media\sources\boot.wim" /Index:1 /MountDir:"C:\WinPE_amd64_PS\mount"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\WinPE-WMI.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\en-us\WinPE-WMI_en-us.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\WinPE-NetFX.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\en-us\WinPE-NetFX_en-us.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\WinPE-Scripting.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\en-us\WinPE-Scripting_en-us.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\WinPE-PowerShell.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\en-us\WinPE-PowerShell_en-us.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\WinPE-StorageWMI.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\en-us\WinPE-StorageWMI_en-us.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\WinPE-DismCmdlets.cab"

Dism /Add-Package /Image:"C:\WinPE_amd64_PS\mount" /PackagePath:"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\amd64\WinPE_OCs\en-us\WinPE-DismCmdlets_en-us.cab"

Dism /Unmount-Image /MountDir:C:\WinPE_amd64_PS\mount /Commit
```

- run the script ```addingPowershell.bat```

### Edit the winpe startup environment
- Mount the winpe image
```Dism /Mount-Image /ImageFile:"C:\WinPE_amd64_PS\media\sources\boot.wim" /Index:1 /MountDir:"C:\WinPE_amd64_PS\mount"```
- Edit the winpe startup file
After the image is mounted,  edit **startnet.cmd** that could be found in: **C:\WinPE_amd64_PS\mount\Windows\System32**.
Add the following to the  **startnet.cmd** file:
```
wpeinit
powershell -ExecutionPolicy ByPass -File startup.ps1
```
- Create a script named **startup.ps1**  in the same directory 
The script content could be found here:
https://github.com/RackHD/on-taskgraph/blob/master/data/templates/startup.ps1

- unmount the winpe image
```
Dism /Unmount-Image /MountDir:C:\WinPE_amd64_PS\mount /Commit```

###Copy the winpe files to on-http server directory
All the winpe files that are listed in the windows.ipxe profile (the link below) should be moved to the appropriate directories
https://github.com/RackHD/on-http/blob/master/data/profiles/windows.ipxe 

The required files/directories could be found in:
**wimboot** is the kernel, and the latest version could be found here http://git.ipxe.org/releases/wimboot/wimboot-latest.zip 
**bootmgr** is located in : C:\WinPE_amd64_PS\media
**Boot** is located in : C:\WinPE_amd64_PS\media
**boot.wim** is located in C:\WinPE_amd64_PS\media\sources

The directory structure would look something like this:
```
onrack@ORA:/var/renasar/on-http/static/http/winpe$ ls
amd64  Boot  bootmgr  wimboot
```
