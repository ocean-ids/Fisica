import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-patron-sacafrancos-modal',
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, MatButtonModule, MatChipsModule, MatDialogModule],
  templateUrl: './patron-sacafrancos-modal.component.html',
  styleUrl: './patron-sacafrancos-modal.component.css'
})
export class PatronSacafrancosModalComponent {
  lista: any[] = [];
  weekStart?: string;
  day?: string;

  constructor(
    public dialogRef: MatDialogRef<PatronSacafrancosModalComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {
    this.lista = data?.lista || [];
    this.weekStart = data?.weekStart;
    this.day = data?.day;
  }

  close(): void {
    this.dialogRef.close();
  }

  onSelect(event: any) {
    const selected = event?.value;
    this.dialogRef.close(selected);
  }

  displayStatus(status: string|undefined|null) {
    if (!status) { return ''; }
    const s = status.toString().toLowerCase();
    if (s === 'available') { return 'Disponible'; }
    if (s === 'assigned' || s === 'asignado') { return 'Asignado'; }
    // fallback: capitalize first letter
    return status.toString();
  }

  getChipColor(status: string|undefined|null) {
    if (!status) { return '';
    }
    return status.toString().toLowerCase() === 'available' ? 'primary' : 'warn';
  }
}
