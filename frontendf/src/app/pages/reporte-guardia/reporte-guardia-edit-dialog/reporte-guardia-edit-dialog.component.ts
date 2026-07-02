import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { ReporteGuardia } from '../../../models/reporte-guardia.model';

@Component({
  selector: 'app-reporte-guardia-edit-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatDialogModule,
    MatFormFieldModule, MatInputModule, MatButtonModule,
  ],
  templateUrl: './reporte-guardia-edit-dialog.component.html',
  styleUrl: './reporte-guardia-edit-dialog.component.css',
})
export class ReporteGuardiaEditDialogComponent {
  motivo: string;

  constructor(
    private dialogRef: MatDialogRef<ReporteGuardiaEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public row: ReporteGuardia,
  ) {
    this.motivo = row.motivo || '';
  }

  guardar(): void {
    this.dialogRef.close({ motivo: (this.motivo || '').trim() });
  }

  cancelar(): void {
    this.dialogRef.close();
  }
}
