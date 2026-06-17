import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AuthService } from '../../services/auth.service';

export interface ProfileDialogData {
  fullName: string;
  photoUrl?: string | null;
}

@Component({
  selector: 'app-profile-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  templateUrl: './profile-dialog.component.html',
  styleUrl: './profile-dialog.component.css'
})
export class ProfileDialogComponent {
  fullName = '';
  photoPreview: string | null = null;
  selectedFile: File | null = null;
  saving = false;
  errorText = '';

  constructor(
    private authService: AuthService,
    private dialogRef: MatDialogRef<ProfileDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ProfileDialogData
  ) {
    this.fullName = data?.fullName || '';
    this.photoPreview = data?.photoUrl || null;
  }

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input?.files?.[0] || null;
    this.selectedFile = file;
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      this.photoPreview = String(reader.result || '');
    };
    reader.readAsDataURL(file);
  }

  save(): void {
    if (this.saving || !this.selectedFile) {
      this.dialogRef.close({ updated: false });
      return;
    }
    this.saving = true;
    this.errorText = '';
    this.authService.updateProfilePhoto(this.selectedFile).subscribe({
      next: (profile) => {
        this.saving = false;
        this.dialogRef.close({ updated: true, profile });
      },
      error: () => {
        this.saving = false;
        this.errorText = 'No se pudo actualizar la foto.';
      }
    });
  }

  cancel(): void {
    if (this.saving) return;
    this.dialogRef.close({ updated: false });
  }

  removePhoto(): void {
    if (this.saving) return;
    this.saving = true;
    this.errorText = '';
    this.authService.updateProfilePhoto(null, true).subscribe({
      next: (profile) => {
        this.saving = false;
        this.photoPreview = null;
        this.selectedFile = null;
        this.dialogRef.close({ updated: true, profile });
      },
      error: () => {
        this.saving = false;
        this.errorText = 'No se pudo quitar la foto.';
      }
    });
  }
}
