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

export interface ConsolidadoFormDialogData {
  row: ConsolidadoRow;
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
  oceanInstalaciones: any[] = [];
  oceanPuestos: Puesto[] = [];
  loadingInstalaciones = false;
  loadingPuestos = false;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<ConsolidadoFormComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConsolidadoFormDialogData,
    private instalacionService: InstalacionService,
    private puestoService: PuestoService
  ) {
    const tipo = (data.row?.tipo || '').toString().toUpperCase();
    this.isConsola = tipo.startsWith('CONS');
    this.form = this.fb.group({
      nominativo: [data.row?.nominativo || '', Validators.maxLength(50)],
      proyecto: [data.row?.proyecto || '', Validators.maxLength(120)],
      puesto: [data.row?.puesto || '', Validators.maxLength(120)],
      observacion: [data.row?.observacion || '', Validators.maxLength(200)]
    });

    if (this.isConsola) {
      this.loadOceanInstalaciones();
    }
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
        this.oceanPuestos = Array.isArray(rows) ? rows : [];
      },
      error: () => {
        this.oceanPuestos = [];
      },
      complete: () => {
        this.loadingPuestos = false;
      }
    });
  }

  cerrar(): void {
    this.dialogRef.close();
  }

  guardar(): void {
    if (this.form.invalid) return;
    this.dialogRef.close({
      nominativo: this.form.value.nominativo || '',
      proyecto: this.form.value.proyecto || '',
      puesto: this.form.value.puesto || '',
      observacion: this.form.value.observacion || ''
    });
  }
}
