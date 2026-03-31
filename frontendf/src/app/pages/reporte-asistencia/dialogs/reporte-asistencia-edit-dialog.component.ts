import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { ReporteAsistenciaService } from '../../../services/reporte-asistencia.service';
import { ReporteAsistenciaRow, UpdateReporteAsistenciaPayload } from '../../../models';
import { PersonaService } from '../../../services/persona.service';
import { Persona } from '../../../models';


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
  readonly tiposReemplazoPermitidos = new Set([
    'FIJOS',
    'SACAFRANCO',
    'RETENES',
    'EVENTUALES',
    'SACAVACACIONES',
    'SUPERVISOR MOTORIZADO',
    'SUPERVISOR ZONAL'
  ]);

  reemplazos: Persona[] = [];
  cargandoReemplazos = false;
  guardando = false;
  error = '';
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private reporteSvc: ReporteAsistenciaService,
    private personaSvc: PersonaService,
    private dialogRef: MatDialogRef<ReporteAsistenciaEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { row: ReporteAsistenciaRow; fecha?: string | null }
  ) {
    this.dialogRef.disableClose = true;
    this.form = this.fb.group({
      codigo: [data?.row?.codigo ?? ''],
      estado: [data?.row?.estado || 'TURNO', Validators.required],
      reemplazo_id: [data?.row?.reemplazo_id ?? null],
      descripcion: [data?.row?.descripcion ?? '']
    });

    this.cargarReemplazos();
  }

  private cargarReemplazos(): void {
    this.cargandoReemplazos = true;
    this.personaSvc.getPersonas().subscribe({
      next: (data) => {
        const list = Array.isArray(data) ? data : [];
        this.reemplazos = list.filter((p) =>
          !!p?.id &&
          p?.is_active !== false &&
          this.tiposReemplazoPermitidos.has(String(p?.tipo || ''))
        );
      },
      error: (err) => {
        console.error('Error al cargar reemplazos', err);
        this.error = 'No se pudo cargar la lista de reemplazos.';
      },
      complete: () => {
        this.cargandoReemplazos = false;
      }
    });
  }


  getNombrePersona(p: Persona): string {
    return `${p.nombres || ''} ${p.apellidos || ''}`.trim();
  }

  cancelar(): void {
    if (this.guardando) return;
    this.dialogRef.close();
  }

  guardar(): void {
    if (this.guardando || this.form.invalid || !this.data?.row?.asignacion_id) return;

    const payload: UpdateReporteAsistenciaPayload = {
      codigo: this.form.value.codigo === '' ? null : this.form.value.codigo,
      estado: this.form.value.estado || null,
      reemplazo_id: this.form.value.reemplazo_id === '' ? null : this.form.value.reemplazo_id,
      descripcion: this.form.value.descripcion === '' ? null : this.form.value.descripcion,
      fecha: this.data?.fecha || null
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
        this.error = err?.error?.error || err?.error?.detail || 'No se pudo guardar la actualizacion.';
        console.error('Error al actualizar reporte de asistencia', err);
      }
    });
  }
}
