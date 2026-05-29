import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
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
    MatAutocompleteModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule
  ],
  templateUrl: './reporte-asistencia-edit-dialog.component.html',
  styleUrl: './reporte-asistencia-edit-dialog.component.css'
})
export class ReporteAsistenciaEditDialogComponent {
  readonly estadosDisponibles = ['TURNO', 'ADICIONAL', 'EVENTUAL', 'ADEL/TURNO', 'DOBLA', 'FR/TRABAJADO', 'RETEN', 'CUSTODIO'];
  readonly estadosAsistenciaDisponibles: Array<'ASISTIO' | 'FALTO'> = ['ASISTIO', 'FALTO'];
  readonly tiposReemplazoPermitidos = new Set([
    'FIJOS',
    'SACAFRANCO',
    'RETEN',
    'EVENTUAL',
    'SACAVACACIONES',
    'SUPERVISOR MOTORIZADO',
    'SUPERVISOR ZONAL'
  ]);

  reemplazos: Persona[] = [];
  reemplazoCtrl = new FormControl<Persona | string | null>('');
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
      estado: [data?.row?.estado || 'TURNO', Validators.required],
      estado_asistencia: [data?.row?.estado_asistencia ?? null],
      reemplazo_id: [data?.row?.reemplazo_id ?? null],
      descripcion: [data?.row?.descripcion ?? '']
    });

    this.reemplazoCtrl.setValue(data?.row?.reemplazo || '', { emitEvent: false });
    this.reemplazoCtrl.valueChanges.subscribe((value) => {
      if (typeof value === 'string') {
        this.form.get('reemplazo_id')?.setValue(null, { emitEvent: false });
      }
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

        const selectedId = this.form.get('reemplazo_id')?.value;
        if (selectedId) {
          const selectedPersona = this.reemplazos.find(p => p.id === selectedId);
          if (selectedPersona) {
            this.reemplazoCtrl.setValue(selectedPersona, { emitEvent: false });
          }
        }
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

  private normalizeText(value: string | null | undefined): string {
    if (!value) return '';
    return value.toString().trim().toUpperCase().replace(/[^A-Z0-9]+/g, '');
  }

  displayReemplazo = (value: Persona | string | null): string => {
    if (!value) return '';
    if (typeof value === 'string') return value;
    return this.getNombrePersona(value);
  };

  onReemplazoOptionSelected(value: Persona | null): void {
    this.form.get('reemplazo_id')?.setValue(value?.id ?? null);
  }

  getReemplazosFiltrados(): Persona[] {
    const currentValue = this.reemplazoCtrl.value;
    const query = typeof currentValue === 'string'
      ? currentValue
      : (currentValue ? this.getNombrePersona(currentValue) : '');
    const q = this.normalizeText(query);
    if (!q) return this.reemplazos;

    return this.reemplazos.filter((p) => {
      const fullName = this.normalizeText(`${p.apellidos || ''} ${p.nombres || ''}`);
      const tipo = this.normalizeText(p.tipo || '');
      return fullName.includes(q) || tipo.includes(q);
    });
  }

  cancelar(): void {
    if (this.guardando) return;
    this.dialogRef.close();
  }

  guardar(): void {
    if (this.guardando || this.form.invalid || !this.data?.row?.asignacion_id) return;

    const payload: UpdateReporteAsistenciaPayload = {
      estado: this.form.value.estado || null,
      estado_asistencia: this.form.value.estado_asistencia || null,
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
