@echo off
git clone -n --depth=1 https://github.com/microsoft/terminal/
git --git-dir=terminal/.git checkout main -- src/cascadia/CascadiaPackage/ProfileIcons/*-200.png
git --git-dir=terminal/.git checkout main -- res/terminal/images/Square44x44Logo.targetsize-96.png
move src\cascadia\CascadiaPackage\ProfileIcons\*-200.png .
move res\terminal\images\Square44x44Logo.targetsize-96.png WindowsTerminal.png
rd /s /q terminal src res
