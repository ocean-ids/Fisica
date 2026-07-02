import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { ReporteGuardia } from '../../../models/reporte-guardia.model';

interface DialogData {
  row: ReporteGuardia;
  campos: string[];                    // solo las columnas de esa sección (sin 'motivo')
  etiquetas: Record<string, string>;
}

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
  row: ReporteGuardia;
  campos: string[];
  etiquetas: Record<string, string>;
  motivo: string;

  constructor(
    private dialogRef: MatDialogRef<ReporteGuardiaEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
  ) {
    this.row = data.row;
    this.campos = data.campos || [];
    this.etiquetas = data.etiquetas || {};
    this.motivo = data.row.motivo || '';
  }

  mostrar(campo: string): string {
    const v = (this.row as any)?.[campo];
    if (campo === 'fecha_evento' || campo === 'fecha') {
      if (!v) { return '-'; }
      const [y, m, d] = String(v).slice(0, 10).split('-');
      return (y && m && d) ? `${d}/${m}/${y}` : String(v);
    }
    if (campo === 'valor') { return v ? Number(v).toFixed(2) : '-'; }
    return (v ?? '') === '' ? '-' : String(v);
  }

  guardar(): void {
    this.dialogRef.close({ motivo: (this.motivo || '').trim() });
  }

  cancelar(): void {
    this.dialogRef.close();
  }
}
