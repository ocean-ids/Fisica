import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';

export interface ColorOption {
  name: string;
  value: string;
}

export interface ReporteAsistenciaColorDialogData {
  selectedColor: string;
  palette: ColorOption[];
}

@Component({
  selector: 'app-reporte-asistencia-color-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule],
  templateUrl: './reporte-asistencia-color-dialog.component.html',
  styleUrl: './reporte-asistencia-color-dialog.component.css'
})
export class ReporteAsistenciaColorDialogComponent {
  selectedColor: string;

  constructor(
    private dialogRef: MatDialogRef<ReporteAsistenciaColorDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ReporteAsistenciaColorDialogData
  ) {
    this.selectedColor = data?.selectedColor || data?.palette?.[0]?.value || '#fff8b3';
  }

  selectColor(color: string): void {
    this.selectedColor = color;
  }

  cancel(): void {
    this.dialogRef.close();
  }

  accept(): void {
    this.dialogRef.close(this.selectedColor);
  }
}
