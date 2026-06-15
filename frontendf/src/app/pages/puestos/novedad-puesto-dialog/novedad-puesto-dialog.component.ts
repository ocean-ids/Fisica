import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { NovedadPuesto } from '../../../models/novedad-puesto.model';

interface DialogData {
  puestos?: any[];
  clienteNombre?: string;
  fecha?: string;
}

@Component({
  selector: 'app-novedad-puesto-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatDialogModule, MatFormFieldModule,
    MatInputModule, MatSelectModule, MatButtonModule
  ],
  templateUrl: './novedad-puesto-dialog.component.html',
  styleUrl: './novedad-puesto-dialog.component.css'
})
export class NovedadPuestoDialogComponent implements OnInit {
  puestos: any[] = [];
  puestoId: number | null = null;

  model: NovedadPuesto = {
    fecha: '',
    turno: 'Diurno',
    cliente_denominativo: '',
    sector: '',
    novedad: 'MODIFICACION',
    tipo: '',
    horario: '',
    solicitado_por: '',
    observacion: '',
    puesto: null,
    instalacion: null,
  };

  novedades = [
    { value: 'APERTURA', label: 'Apertura' },
    { value: 'MODIFICACION', label: 'Modificación' },
    { value: 'CIERRE', label: 'Cierre' },
    { value: 'INCREMENTO', label: 'Incremento' },
    { value: 'MODIFICACION INCREMENTO', label: 'Modificación / Incremento' },
  ];

  constructor(
    private dialogRef: MatDialogRef<NovedadPuestoDialogComponent, NovedadPuesto | null>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData | null
  ) {}

  ngOnInit(): void {
    this.puestos = this.data?.puestos || [];
    this.model.fecha = this.data?.fecha || this.hoyISO();
    if (this.data?.clienteNombre) {
      this.model.cliente_denominativo = this.data.clienteNombre;
    }
  }

  private hoyISO(): string {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${mm}-${dd}`;
  }

  onPuestoChange(): void {
    const p = this.puestos.find(x => x.id === this.puestoId);
    if (!p) {
      this.model.puesto = null;
      this.model.instalacion = null;
      return;
    }
    this.model.puesto = p.id;
    this.model.instalacion = p.instalacion_id ?? null;

    const denom = (p.instalacion_codigo || p.instalacion_nombre || '').toString().trim();
    const cliente = (this.data?.clienteNombre || '').trim();
    this.model.cliente_denominativo = denom
      ? (cliente ? `${cliente} - ${denom}` : denom)
      : cliente;

    this.model.sector = (p.instalacion_sector || '').toString();
    this.model.tipo = (p.tipo || p.resumen || '').toString();

    const horas = (p.horarios || [])
      .map((h: any) => h.horas)
      .filter((h: any) => h !== null && h !== undefined);
    this.model.horario = horas.length ? horas.join(',') : '';

    const turno = (p.turno || '').toString().toLowerCase();
    if (turno.startsWith('n')) this.model.turno = 'Nocturno';
    else if (turno.startsWith('d')) this.model.turno = 'Diurno';
  }

  isValid(): boolean {
    return !!this.model.fecha && !!this.model.novedad && !!this.model.cliente_denominativo.trim();
  }

  guardar(): void {
    if (!this.isValid()) return;
    this.dialogRef.close({ ...this.model });
  }

  cancelar(): void {
    this.dialogRef.close(null);
  }
}
