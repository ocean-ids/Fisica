import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { ReporteAsistenciaService } from '../../services/reporte-asistencia.service';

type ReporteRow = {
  asignacion_id?: number;
  cliente?: string;
  puesto?: string;
  horario?: string;
  nombre_apellidos?: string;
  codigo?: string;
  estado?: string;
  descripcion?: string;
  modificado_por?: string;
  modificado_en?: string;
};

@Component({
  selector: 'app-reporte-asistencia-edit-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule
  ],
  templateUrl: './reporte-asistencia-edit-dialog.component.html',
  styleUrl: './reporte-asistencia-edit-dialog.component.css'
})
export class ReporteAsistenciaEditDialogComponent {
  readonly estadosDisponibles = ['TURNO', 'ADICIONAL', 'EVENTUAL', 'ADEL/TURNO'];
  guardando = false;
  error = '';
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private reporteSvc: ReporteAsistenciaService,
    private dialogRef: MatDialogRef<ReporteAsistenciaEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { row: ReporteRow }
  ) {
    this.dialogRef.disableClose = true;
    this.form = this.fb.group({
      codigo: [data?.row?.codigo ?? ''],
      estado: [data?.row?.estado || 'TURNO', Validators.required],
      descripcion: [data?.row?.descripcion ?? '']
    });
  }

  cancelar(): void {
    if (this.guardando) return;
    this.dialogRef.close();
  }

  guardar(): void {
    if (this.guardando || this.form.invalid || !this.data?.row?.asignacion_id) return;

    const payload = {
      codigo: this.form.value.codigo === '' ? null : this.form.value.codigo,
      estado: this.form.value.estado || null,
      descripcion: this.form.value.descripcion === '' ? null : this.form.value.descripcion
    };

    this.guardando = true;
    this.error = '';

    this.reporteSvc.updateReporteAsistencia(this.data.row.asignacion_id, payload).subscribe({
      next: (res) => {
        this.guardando = false;
        this.dialogRef.close(res);
      },
      error: (err) => {
        this.guardando = false;
        this.error = err?.error?.detail || 'No se pudo guardar la actualizacion.';
        console.error('Error al actualizar reporte de asistencia', err);
      }
    });
  }
}
