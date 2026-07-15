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
  campos: string[];                    // columnas de solo lectura de esa sección
  editables: string[];                 // campos editables (p. ej. autorizacion, motivo)
  etiquetas: Record<string, string>;
  titulo?: string;                     // título del diálogo (p. ej. "Crear apoyo")
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
  editables: string[];
  etiquetas: Record<string, string>;
  titulo: string;
  valores: Record<string, string> = {};

  constructor(
    private dialogRef: MatDialogRef<ReporteGuardiaEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
  ) {
    this.row = data.row;
    this.campos = data.campos || [];
    this.editables = (data.editables && data.editables.length) ? data.editables : ['motivo'];
    this.etiquetas = data.etiquetas || {};
    this.titulo = data.titulo || `Editar registro — ${data.row?.seccion || ''}`;
    for (const campo of this.editables) {
      const raw = (this.row as any)?.[campo];
      if (campo === 'fecha_evento' || campo === 'fecha') {
        this.valores[campo] = raw ? String(raw).slice(0, 10) : '';
      } else {
        this.valores[campo] = (raw ?? '').toString();
      }
    }
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

  // Tipo de input HTML según el campo.
  tipoInput(campo: string): 'number' | 'date' | 'text' {
    if (campo === 'valor') { return 'number'; }
    if (campo === 'fecha_evento' || campo === 'fecha') { return 'date'; }
    return 'text';
  }

  // ¿Se muestra como textarea (texto largo) en vez de input de una línea?
  esTextarea(campo: string): boolean {
    return campo === 'motivo' || campo === 'autorizacion';
  }

  guardar(): void {
    const out: Record<string, any> = {};
    for (const campo of this.editables) {
      const v = (this.valores[campo] ?? '').toString().trim();
      if (campo === 'valor') {
        out[campo] = v === '' ? 0 : Number(v);
      } else if (campo === 'fecha_evento' || campo === 'fecha') {
        out[campo] = v === '' ? null : v;
      } else {
        out[campo] = v;
      }
    }
    this.dialogRef.close(out);
  }

  cancelar(): void {
    this.dialogRef.close();
  }
}
