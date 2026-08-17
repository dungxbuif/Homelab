#!/bin/bash
set -e

# Configuration
VM_ID=9000
VM_NAME="ubuntu-22.04-template"
DISK_SIZE="20G"
STORAGE="local-lvm"
IMAGE_URL="https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img"
IMAGE_NAME="jammy-server-cloudimg-amd64.img"

cd /root

# Download image
if [ ! -f "$IMAGE_NAME" ]; then
    echo "Downloading Ubuntu Cloud Image..."
    wget -q "$IMAGE_URL" -O "$IMAGE_NAME"
fi

# Create VM
if qm status $VM_ID >/dev/null 2>&1; then
    echo "VM $VM_ID already exists. Deleting..."
    qm destroy $VM_ID
fi

echo "Creating VM $VM_ID..."
qm create $VM_ID --name $VM_NAME --memory 2048 --net0 virtio,bridge=vmbr0

# Import disk
echo "Importing disk..."
qm importdisk $VM_ID $IMAGE_NAME $STORAGE

# Configure VM
echo "Configuring VM..."
qm set $VM_ID --scsihw virtio-scsi-pci --scsi0 $STORAGE:vm-$VM_ID-disk-0
qm set $VM_ID --ide2 $STORAGE:cloudinit
qm set $VM_ID --boot c --bootdisk scsi0
qm set $VM_ID --serial0 socket --vga serial0

# Resize disk
echo "Resizing disk to $DISK_SIZE..."
qm resize $VM_ID scsi0 $DISK_SIZE

# Convert to template
echo "Converting to template..."
qm template $VM_ID

echo "Template $VM_ID ($VM_NAME) created successfully."
