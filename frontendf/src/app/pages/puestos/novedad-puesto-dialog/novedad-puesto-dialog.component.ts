import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { NovedadPuesto } from '../../../models/novedad-puesto.model';
import { PuestoService } from '../../../services/puesto.service';

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
    private puestoService: PuestoService,
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

  // APERTURA -> solo puestos CERRADOS (reabrir). Resto (cierre, etc.) -> solo ACTIVOS.
  get puestosFiltrados(): any[] {
    const esApertura = (this.model.novedad || '').toString().toUpperCase() === 'APERTURA';
    return (this.puestos || []).filter(p =>
      esApertura ? p.activo === false : p.activo !== false
    );
  }

  onNovedadChange(): void {
    // Si el puesto elegido ya no aplica al tipo de novedad, limpiarlo.
    if (this.puestoId != null && !this.puestosFiltrados.some(p => p.id === this.puestoId)) {
      this.puestoId = null;
      this.onPuestoChange();
    }
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
    // Tipo = resumen de horario (fallback al resumen local mientras llega el endpoint)
    this.model.tipo = (p.resumen || '').toString();
    // Horario = secuencia de rotación D/N/F del calendario (ej. "3,3,2")
    this.model.horario = '';

    const turno = (p.turno || '').toString().toLowerCase();
    if (turno.startsWith('n')) this.model.turno = 'Nocturno';
    else if (turno.startsWith('d')) this.model.turno = 'Diurno';

    // Trae la secuencia real del calendario y el resumen desde el backend.
    this.puestoService.getSecuenciaHorario(p.id).subscribe({
      next: (res) => {
        if (res?.secuencia) this.model.horario = res.secuencia;
        if (res?.resumen) this.model.tipo = res.resumen;
      },
      error: () => {}
    });
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
