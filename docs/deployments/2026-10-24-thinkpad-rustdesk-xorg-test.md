# ThinkPad RustDesk Xorg diagnostic

User approved a reversible Xorg test on ThinkPad 10.10.0.13 to investigate
keyboard input failing when remotely controlling macOS while mouse works.
Both Xorg session files and xserver-xorg-core are installed; current desktop
was Wayland. This is a diagnostic hypothesis, not a confirmed root cause.

Change: back up /etc/gdm3/custom.conf, then uncomment WaylandEnable=false.
This affects GDM globally. Do not restart GDM or reboot without ensuring the
user has saved work. No credentials are stored in this document.

Verify config immediately; after user reboot/login, check loginctl session Type
is x11 and test remote typing into TextEdit, then separately the lock screen.
Rollback: restore the timestamped config backup and reboot after saving work.
Public docs unchanged: this is an internal workstation diagnostic only.

Applied: line 7 verified as WaylandEnable=false. Backup saved on ThinkPad at
/etc/gdm3/custom.conf.before-xorg-20261024-095021. No reboot or GDM restart
performed. X11 session and remote keyboard verification remain pending.

After user reboot: loginctl confirms local dungxbuif session Type=x11 and
State=active; configuration remains WaylandEnable=false. No lowercase rustdesk
process matched pgrep at that check. User must open the client and verify typing;
the keyboard issue is not yet confirmed fixed.
