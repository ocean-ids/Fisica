import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { ConsolidadoRow } from '../../../models/consolidado.model';
import { InstalacionService } from '../../../services/instalacion.service';
import { PuestoService } from '../../../services/puesto.service';
import { Puesto } from '../../../models/puesto.model';
import { PersonaService } from '../../../services/persona.service';
import { Persona } from '../../../models';

export interface ConsolidadoFormDialogData {
  row: ConsolidadoRow;
  mode?: 'create' | 'edit';
}

@Component({
  selector: 'app-consolidado-form',
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
  templateUrl: './consolidado-form.component.html',
  styleUrl: './consolidado-form.component.css'
})
export class ConsolidadoFormComponent {
  form: FormGroup;
  isConsola: boolean;
  isCreateMode: boolean;
  currentTurno: string;
  oceanInstalaciones: any[] = [];
  oceanPuestos: Puesto[] = [];
  personasConsola: Persona[] = [];
  loadingInstalaciones = false;
  loadingPuestos = false;
  loadingPersonas = false;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<ConsolidadoFormComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConsolidadoFormDialogData,
    private instalacionService: InstalacionService,
    private puestoService: PuestoService,
    private personaService: PersonaService
  ) {
    const tipo = (data.row?.tipo || '').toString().toUpperCase();
    this.isConsola = tipo.startsWith('CONS');
    this.isCreateMode = (data.mode || 'edit') === 'create';
    this.currentTurno = (data.row?.turno || '').toString().trim().toUpperCase();
    this.form = this.fb.group({
      persona_ref_id: [data.row?.persona_ref_id || null],
      nominativo: [data.row?.nominativo || '', Validators.maxLength(50)],
      proyecto: [data.row?.proyecto || '', Validators.maxLength(120)],
      puesto: [data.row?.puesto || '', Validators.maxLength(120)],
      observacion: [data.row?.observacion || '', Validators.maxLength(200)]
    });

    if (this.isConsola && this.isCreateMode) {
      this.form.get('persona_ref_id')?.setValidators([Validators.required]);
      this.form.get('persona_ref_id')?.updateValueAndValidity();
    }

    if (this.isConsola) {
      this.loadOceanInstalaciones();
      if (this.isCreateMode) {
        this.loadPersonasConsola();
      }
    }
  }

  get personaDisplayNombre(): string {
    if (!this.isCreateMode) {
      return `${this.data.row.apellidos || ''} ${this.data.row.nombres || ''}`.trim() || '-';
    }
    const id = Number(this.form.value.persona_ref_id || 0);
    const p = this.personasConsola.find(x => x.id === id);
    if (!p) return '-';
    return `${p.apellidos || ''} ${p.nombres || ''}`.trim() || '-';
  }

  get personaEstado(): string {
    if (!this.isCreateMode) {
      return this.data.row.estado || '-';
    }
    const id = Number(this.form.value.persona_ref_id || 0);
    const p = this.personasConsola.find(x => x.id === id);
    return p?.tipo || '-';
  }

  private loadPersonasConsola(): void {
    this.loadingPersonas = true;
    this.personaService.getPersonas().subscribe({
      next: (rows) => {
        const list = Array.isArray(rows) ? rows : [];
        this.personasConsola = list.filter((p: Persona) => {
          const tipo = (p?.tipo || '').toString().toUpperCase();
          return p?.is_active !== false && (tipo === 'OPERADOR CENTRO CONTROL' || tipo === 'SUPERVISOR CENTRO CONTROL');
        });
      },
      error: () => {
        this.personasConsola = [];
      },
      complete: () => {
        this.loadingPersonas = false;
      }
    });
  }

  private loadOceanInstalaciones(): void {
    this.loadingInstalaciones = true;
    this.instalacionService.getInstalaciones({ cliente: 'OCEAN' }).subscribe({
      next: (rows) => {
        const list = Array.isArray(rows) ? rows : [];
        this.oceanInstalaciones = list.filter((inst: any) => {
          const name = (inst?.cliente_nombre || inst?.nombre_cliente || '').toString().toUpperCase();
          return name.includes('OCEAN');
        });
        const proyecto = (this.form.value.proyecto || '').toString().trim();
        if (proyecto) {
          const match = this.oceanInstalaciones.find(i => (i?.nombre || '') === proyecto);
          if (match?.id) {
            this.loadPuestos(match.id);
          }
        }
      },
      error: () => {
        this.oceanInstalaciones = [];
      },
      complete: () => {
        this.loadingInstalaciones = false;
      }
    });
  }

  setNominativo(value: string): void {
    const codigo = value || '';
    const match = this.oceanInstalaciones.find(i => (i?.codigo || '') === codigo);
    this.form.patchValue({
      nominativo: codigo,
      proyecto: match?.nombre || this.form.value.proyecto || ''
    });
    if (match?.id) {
      this.loadPuestos(match.id);
    }
  }

  setProyecto(value: string): void {
    const proyecto = value || '';
    const match = this.oceanInstalaciones.find(i => (i?.nombre || '') === proyecto);
    this.form.patchValue({
      proyecto,
      nominativo: match?.codigo || this.form.value.nominativo || ''
    });
    if (match?.id) {
      this.loadPuestos(match.id);
    }
  }

  private loadPuestos(instalacionId: number): void {
    this.loadingPuestos = true;
    this.puestoService.getPuestosPorInstalacion(instalacionId).subscribe({
      next: (rows) => {
        const list = Array.isArray(rows) ? rows : [];
        this.oceanPuestos = list.filter((p: Puesto) => this.isPuestoCompatibleConTurno(p));
      },
      error: () => {
        this.oceanPuestos = [];
      },
      complete: () => {
        this.loadingPuestos = false;
      }
    });
  }

  private isPuestoCompatibleConTurno(puesto: Puesto): boolean {
    if (!this.currentTurno) {
      return true;
    }

    const labels = new Set<string>();

    const turno = (puesto?.turno || '').toString().trim().toUpperCase();
    const turnoDisplay = (puesto?.turno_display || '').toString().trim().toUpperCase();
    if (turno) labels.add(turno);
    if (turnoDisplay) labels.add(turnoDisplay);

    const horarios = Array.isArray(puesto?.horarios) ? puesto.horarios : [];
    for (const h of horarios) {
      const t = (h?.turno || '').toString().trim().toUpperCase();
      if (t) labels.add(t);
    }

    const is24h = labels.has('24H') || labels.has('AMBOS');
    if (is24h) {
      return true;
    }

    if (this.currentTurno === 'DIURNO') {
      return labels.has('DIURNO');
    }

    if (this.currentTurno === 'NOCTURNO') {
      return labels.has('NOCTURNO');
    }

    return true;
  }

  cerrar(): void {
    this.dialogRef.close();
  }

  guardar(): void {
    if (this.form.invalid) return;
    this.dialogRef.close({
      persona_ref_id: this.form.value.persona_ref_id || null,
      nominativo: this.form.value.nominativo || '',
      proyecto: this.form.value.proyecto || '',
      puesto: this.form.value.puesto || '',
      observacion: this.form.value.observacion || ''
    });
  }
}
