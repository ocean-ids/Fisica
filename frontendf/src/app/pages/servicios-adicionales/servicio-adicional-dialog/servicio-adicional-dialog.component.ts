import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import Swal from 'sweetalert2';
import {
  CatalogoServiciosAdicionales, ServicioAdicional, ServiciosAdicionalesService,
} from '../../../services/servicios-adicionales.service';
import { AuthService } from '../../../services/auth.service';

type Opcion = { id: number; nombre: string; cliente_id?: number };

// Formulario del Servicio Adicional (FR-REPORTE DE PUESTO ADICIONAL). Se abre desde el módulo (Nuevo / editar)
// o desde la asistencia al guardar una fila como ADICIONAL, ya prellenado (cliente y horario de ese registro).
@Component({
  selector: 'app-servicio-adicional-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, MatDialogModule, MatFormFieldModule, MatInputModule,
    MatAutocompleteModule, MatButtonModule, MatButtonToggleModule],
  templateUrl: './servicio-adicional-dialog.component.html',
  styleUrl: './servicio-adicional-dialog.component.css',
})
export class ServicioAdicionalDialogComponent implements OnInit {
  cat: CatalogoServiciosAdicionales | null = null;
  cargando = true;
  guardando = false;
  error = '';

  f: ServicioAdicional = {
    fecha: '', turno: 'Diurno', cliente_id: null, instalacion_id: null, cantidad: 1, horas: 0,
    hora_ingreso: '', hora_salida: '', solicitado_por: '', recibido_por: '', medio: '', precio: null,
  };
  clienteCtrl = new FormControl<any>('');
  instalacionCtrl = new FormControl<any>('');

  constructor(
    private ref: MatDialogRef<ServicioAdicionalDialogComponent>,
    private srv: ServiciosAdicionalesService,
    private auth: AuthService,
    @Inject(MAT_DIALOG_DATA) public data: { row?: Partial<ServicioAdicional>; catalogo?: CatalogoServiciosAdicionales },
  ) {}

  get esEdicion(): boolean { return !!this.f.id; }
  // Editar todo (Consola) / solo el precio (quien tiene ese permiso).
  get puedeEditar(): boolean {
    return this.esEdicion ? this.auth.hasPermission('CoreFisica.change_servicioadicional')
                          : this.auth.hasPermission('CoreFisica.add_servicioadicional');
  }
  get puedePrecio(): boolean { return !!this.cat?.puede_precio; }

  ngOnInit(): void {
    this.f = { ...this.f, ...(this.data?.row || {}) } as ServicioAdicional;
    // Nuevo con horario (por ejemplo, desde la asistencia): H se calcula sola.
    if (!this.f.horas && this.f.hora_ingreso && this.f.hora_salida) { this.recalcularHoras(); }
    const listo = (cat: CatalogoServiciosAdicionales) => {
      this.cat = cat;
      const inst = cat.instalaciones.find(i => i.id === this.f.instalacion_id);
      const cliId = this.f.cliente_id ?? inst?.cliente_id ?? null;
      const cli = cat.clientes.find(c => c.id === cliId);
      if (cli) { this.clienteCtrl.setValue(cli); }
      if (inst) { this.instalacionCtrl.setValue(inst); }
      if (!this.puedeEditar) { this.clienteCtrl.disable(); this.instalacionCtrl.disable(); }
      this.cargando = false;
    };
    if (this.data?.catalogo) { listo(this.data.catalogo); return; }
    this.srv.catalogo().subscribe({ next: listo, error: () => { this.cargando = false; this.error = 'No se pudo cargar la lista de clientes.'; } });
  }

  displayOpcion = (o: any): string => (o && typeof o === 'object') ? (o.nombre || '') : (o || '');

  private norm(s: any): string {
    return (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  private filtrar<T extends Opcion>(lista: T[], valor: any): T[] {
    const q = this.norm(typeof valor === 'string' ? valor : '');
    const r = q ? lista.filter(o => this.norm(o.nombre).includes(q)) : lista;
    return r.slice(0, 80);
  }

  get clientesFiltrados(): Opcion[] { return this.filtrar(this.cat?.clientes || [], this.clienteCtrl.value); }

  get instalacionesFiltradas(): Opcion[] {
    const cli = this.clienteCtrl.value;
    const base = (this.cat?.instalaciones || []).filter(i => !cli || typeof cli !== 'object' || i.cliente_id === cli.id);
    return this.filtrar(base, this.instalacionCtrl.value);
  }

  onClienteSel(): void { this.instalacionCtrl.setValue(''); }

  onInstalacionSel(): void {
    // Al elegir la instalación, el cliente es el de esa instalación.
    const inst = this.instalacionCtrl.value;
    if (inst && typeof inst === 'object' && this.cat) {
      const cli = this.cat.clientes.find(c => c.id === inst.cliente_id);
      if (cli) { this.clienteCtrl.setValue(cli, { emitEvent: false }); }
    }
  }

  limpiar(ctrl: FormControl<any>, ev: Event, cascada = false): void {
    ev.stopPropagation();
    ctrl.setValue('');
    if (cascada) { this.onClienteSel(); }
  }

  // H se calcula sola con el horario (si la salida es antes del ingreso, cruza la medianoche). Se puede cambiar.
  recalcularHoras(): void {
    const a = this.minutos(this.f.hora_ingreso);
    const b = this.minutos(this.f.hora_salida);
    if (a === null || b === null) { return; }
    let d = b - a;
    if (d <= 0) { d += 24 * 60; }
    this.f.horas = Math.round((d / 60) * 100) / 100;
  }

  private minutos(hhmm: string): number | null {
    const m = /^(\d{1,2}):(\d{2})$/.exec((hhmm || '').trim());
    return m ? Number(m[1]) * 60 + Number(m[2]) : null;
  }

  guardar(): void {
    this.error = '';
    const cli = this.clienteCtrl.value;
    const inst = this.instalacionCtrl.value;
    const payload: Partial<ServicioAdicional> = {
      fecha: this.f.fecha, turno: this.f.turno,
      cliente_id: cli && typeof cli === 'object' ? cli.id : null,
      instalacion_id: inst && typeof inst === 'object' ? inst.id : null,
      cantidad: Number(this.f.cantidad) || 0, horas: Number(this.f.horas) || 0,
      hora_ingreso: this.f.hora_ingreso || '', hora_salida: this.f.hora_salida || '',
      solicitado_por: this.f.solicitado_por || '', recibido_por: this.f.recibido_por || '', medio: this.f.medio || '',
      asignacion_id: this.f.asignacion_id ?? null, sacafranco_fila_id: this.f.sacafranco_fila_id ?? null,
    };
    if (this.puedePrecio) {
      payload.precio = (this.f.precio === null || (this.f.precio as any) === '') ? null : Number(this.f.precio);
    }
    if (this.puedeEditar) {
      if (!payload.cliente_id && !payload.instalacion_id) { this.error = 'Elige el cliente.'; return; }
      if (!payload.fecha) { this.error = 'Elige la fecha.'; return; }
      if ((payload.cantidad || 0) < 1) { this.error = 'La cantidad de guardias (C) debe ser al menos 1.'; return; }
    }
    this.guardando = true;
    const obs = this.esEdicion ? this.srv.actualizar(this.f.id!, payload) : this.srv.crear(payload);
    obs.subscribe({
      next: (res) => {
        this.guardando = false;
        Swal.fire({ icon: 'success', title: 'Servicio adicional guardado', timer: 1300, showConfirmButton: false });
        this.ref.close(res);
      },
      error: (err) => {
        this.guardando = false;
        this.error = err?.status === 403 ? 'No tienes permiso para guardar.' : (err?.error?.error || 'No se pudo guardar.');
      },
    });
  }

  cerrar(): void { this.ref.close(); }
}
