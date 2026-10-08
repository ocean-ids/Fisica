import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatSelectModule } from '@angular/material/select';
import Swal from 'sweetalert2';
import {
  CatalogoServiciosAdicionales, ServicioAdicional, ServiciosAdicionalesService,
} from '../../../services/servicios-adicionales.service';
import { AuthService } from '../../../services/auth.service';
import { AsignacionService } from '../../../services/asignacion.service';

type Opcion = { id: number; nombre: string; cliente_id?: number; instalacion_id?: number; tipo?: string; cedula?: string };

// Formulario del Servicio Adicional (FR-REPORTE DE PUESTO ADICIONAL). Se abre:
//  - desde la asistencia al guardar una fila como ADICIONAL, ya prellenado (cliente y horario de ese registro);
//  - con el botón "Agregar Adicional" de la asistencia o "Nuevo registro" del módulo: para clientes y puestos que
//    NO están en el sistema (se escriben a mano) y el guardia que lo cubrió (obligatorio). Va al Reporte de Guardia.
@Component({
  selector: 'app-servicio-adicional-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, MatDialogModule, MatFormFieldModule, MatInputModule,
    MatAutocompleteModule, MatButtonModule, MatButtonToggleModule, MatSelectModule],
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
  puestoCtrl = new FormControl<any>('');
  guardiaCtrl = new FormControl<any>('');

  // Guardia: MISMA lista que el Reemplazo de la asistencia con estado ADICIONAL (mismos tipos, y BACKUP /
  // MOVIMIENTO INTERNO / EN USO). EN USO = ya es reemplazo en otro registro del día (no se puede elegir).
  readonly tiposGuardia = new Set(['FIJOS', 'SACAFRANCO', 'RETEN', 'CUSTODIO', 'EVENTUAL', 'SACAVACACIONES',
    'SUPERVISOR MOTORIZADO', 'SUPERVISOR ZONAL', 'SUPERVISOR EVENTUAL']);
  private enUsoIds = new Set<number>();
  private asignadosIds = new Set<number>();

  constructor(
    private ref: MatDialogRef<ServicioAdicionalDialogComponent>,
    private srv: ServiciosAdicionalesService,
    private auth: AuthService,
    private asignacionSvc: AsignacionService,
    @Inject(MAT_DIALOG_DATA) public data: {
      row?: Partial<ServicioAdicional>; catalogo?: CatalogoServiciosAdicionales;
      occupiedReemplazoIds?: number[];     // reemplazos ya usados en el reporte del día (EN USO)
    },
  ) {
    this.enUsoIds = new Set((data?.occupiedReemplazoIds || []).map(Number).filter(n => n > 0));
  }

  get esEdicion(): boolean { return !!this.f.id; }
  // Agregado a mano (no sale de una fila de la asistencia): lleva puesto y guardia.
  get esManual(): boolean { return !this.f.asignacion_id && !this.f.sacafranco_fila_id; }
  // Editar todo (Consola) / solo el precio (quien tiene ese permiso).
  get puedeEditar(): boolean {
    return this.esEdicion ? this.auth.hasPermission('CoreFisica.change_servicioadicional')
                          : this.auth.hasPermission('CoreFisica.add_servicioadicional');
  }
  get puedePrecio(): boolean { return !!this.cat?.puede_precio; }

  ngOnInit(): void {
    // El aviso de error se borra apenas se escribe o se elige algo.
    [this.clienteCtrl, this.instalacionCtrl, this.puestoCtrl, this.guardiaCtrl]
      .forEach(c => c.valueChanges.subscribe(() => { this.error = ''; }));
    this.f = { ...this.f, ...(this.data?.row || {}) } as ServicioAdicional;
    // Nuevo con horario (por ejemplo, desde la asistencia): H se calcula sola.
    if (!this.f.horas && this.f.hora_ingreso && this.f.hora_salida) { this.recalcularHoras(); }
    const listo = (cat: CatalogoServiciosAdicionales) => {
      this.cat = cat;
      const inst = cat.instalaciones.find(i => i.id === this.f.instalacion_id);
      const cliId = this.f.cliente_id ?? inst?.cliente_id ?? null;
      const cli = cat.clientes.find(c => c.id === cliId);
      // De la lista (objeto) o escrito a mano (texto). Los agregados con el botón siempre van escritos a mano.
      this.clienteCtrl.setValue(this.esManual ? (this.f.cliente_libre || this.f.cliente_texto || '') : (cli || this.f.cliente_libre || ''));
      this.instalacionCtrl.setValue(inst || this.f.instalacion_libre || '');
      const pue = (cat.puestos || []).find(p => p.id === this.f.puesto_id);
      this.puestoCtrl.setValue(this.esManual ? (this.f.puesto_libre || this.f.puesto || '') : (pue || this.f.puesto_libre || ''));
      const per = (cat.personal || []).find(p => p.id === this.f.persona_id);
      this.guardiaCtrl.setValue(per || '');
      if (!this.puedeEditar) {
        [this.clienteCtrl, this.instalacionCtrl, this.puestoCtrl, this.guardiaCtrl].forEach(c => c.disable());
      }
      this.cargando = false;
    };
    // Quién tiene puesto ese mes (MOVIMIENTO INTERNO), igual que en el formulario de la asistencia.
    const [anio, mes] = (this.f.fecha || '').split('-').map(Number);
    if (anio && mes) {
      this.asignacionSvc.obtenerAsignadosYFranco(mes, anio, this.f.fecha).subscribe({
        next: (r) => { this.asignadosIds = new Set((r?.asignados || []).map(Number)); },
        error: () => {},
      });
    }
    if (this.data?.catalogo) { listo(this.data.catalogo); return; }
    this.srv.catalogo().subscribe({ next: listo, error: () => { this.cargando = false; this.error = 'No se pudo cargar la lista de clientes.'; } });
  }

  displayOpcion = (o: any): string => (o && typeof o === 'object') ? (o.nombre || '') : (o || '');

  private norm(s: any): string {
    return (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  private filtrar<T extends Opcion>(lista: T[], valor: any, extra?: (o: T) => string): T[] {
    const q = this.norm(typeof valor === 'string' ? valor : '');
    const r = q ? lista.filter(o => this.norm(o.nombre + ' ' + (extra ? extra(o) : '')).includes(q)) : lista;
    return r.slice(0, 80);
  }

  get clientesFiltrados(): Opcion[] { return this.filtrar(this.cat?.clientes || [], this.clienteCtrl.value); }

  get instalacionesFiltradas(): Opcion[] {
    const cli = this.clienteCtrl.value;
    const base = (this.cat?.instalaciones || []).filter(i => !cli || typeof cli !== 'object' || i.cliente_id === cli.id);
    return this.filtrar(base, this.instalacionCtrl.value);
  }

  get puestosFiltrados(): Opcion[] {
    const inst = this.instalacionCtrl.value;
    // Puestos de la instalación elegida de la lista (si es escrita a mano, el puesto también se escribe).
    if (!inst || typeof inst !== 'object') { return []; }
    return this.filtrar((this.cat?.puestos || []).filter(p => p.instalacion_id === inst.id), this.puestoCtrl.value);
  }

  get guardiasFiltrados(): Opcion[] {
    const base = (this.cat?.personal || []).filter(p => this.tiposGuardia.has(String(p.tipo || '')));
    const lista = this.filtrar(base, this.guardiaCtrl.value, o => `${o.cedula || ''} ${o.tipo || ''}`);
    // Disponibles primero (como en la asistencia).
    return lista.sort((a, b) => (this.enUso(a) ? 1 : 0) - (this.enUso(b) ? 1 : 0));
  }

  enUso(p: Opcion): boolean { return this.enUsoIds.has(Number(p.id)) && Number(p.id) !== Number(this.f.persona_id); }

  etiquetaGuardia(p: Opcion): string {
    if (this.enUso(p)) { return 'EN USO'; }
    return this.asignadosIds.has(Number(p.id)) ? 'MOVIMIENTO INTERNO' : 'BACKUP';
  }

  colorGuardia(p: Opcion): string {
    const e = this.etiquetaGuardia(p);
    return e === 'EN USO' ? '#dc3545' : (e === 'MOVIMIENTO INTERNO' ? '#0891b2' : '#198754');
  }

  // Texto escrito que no es de la lista ("no está en la lista: se guardará tal como lo escribes").
  esLibre(ctrl: FormControl<any>): boolean {
    const v = ctrl.value;
    return typeof v === 'string' && v.trim().length > 0;
  }

  onClienteSel(): void { this.instalacionCtrl.setValue(''); this.puestoCtrl.setValue(''); }

  onInstalacionSel(): void {
    // Al elegir la instalación, el cliente es el de esa instalación.
    const inst = this.instalacionCtrl.value;
    if (inst && typeof inst === 'object' && this.cat) {
      const cli = this.cat.clientes.find(c => c.id === inst.cliente_id);
      if (cli) { this.clienteCtrl.setValue(cli, { emitEvent: false }); }
    }
    this.puestoCtrl.setValue('');
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

  private idDe(ctrl: FormControl<any>): number | null {
    const v = ctrl.value;
    return v && typeof v === 'object' ? v.id : null;
  }

  private textoDe(ctrl: FormControl<any>): string {
    const v = ctrl.value;
    return typeof v === 'string' ? v.trim().toUpperCase() : '';
  }

  guardar(): void {
    this.error = '';
    const payload: Partial<ServicioAdicional> = {
      fecha: this.f.fecha, turno: this.f.turno,
      cliente_id: this.idDe(this.clienteCtrl), cliente_texto: this.textoDe(this.clienteCtrl),
      instalacion_id: this.idDe(this.instalacionCtrl), instalacion_texto: this.textoDe(this.instalacionCtrl),
      cantidad: Number(this.f.cantidad) || 0, horas: Number(this.f.horas) || 0,
      hora_ingreso: this.f.hora_ingreso || '', hora_salida: this.f.hora_salida || '',
      solicitado_por: (this.f.solicitado_por || '').toUpperCase(), recibido_por: (this.f.recibido_por || '').toUpperCase(),
      medio: (this.f.medio || '').toUpperCase(),
      asignacion_id: this.f.asignacion_id ?? null, sacafranco_fila_id: this.f.sacafranco_fila_id ?? null,
    };
    if (this.esManual) {
      // Cliente y puesto que no están en el sistema: solo como texto (sin instalación ni ids de la lista).
      payload.cliente_id = null;
      payload.instalacion_id = null;
      payload.instalacion_texto = '';
      payload.puesto_id = null;
      payload.puesto_texto = this.textoDe(this.puestoCtrl);
      payload.persona_id = this.idDe(this.guardiaCtrl);
    }
    if (this.puedePrecio) {
      payload.precio = (this.f.precio === null || (this.f.precio as any) === '') ? null : Number(this.f.precio);
    }
    if (this.puedeEditar) {
      if (!payload.cliente_id && !payload.instalacion_id && !payload.cliente_texto) {
        this.error = this.esManual ? 'Escribe el cliente.' : 'Elige el cliente.'; return;
      }
      if (!payload.fecha) { this.error = 'Elige la fecha.'; return; }
      if ((payload.cantidad || 0) < 1) { this.error = 'La cantidad de guardias (C) debe ser al menos 1.'; return; }
      if (this.esManual && !payload.persona_id) { this.error = 'Elige de la lista el guardia que cubrió el adicional.'; return; }
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
