import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import Swal from 'sweetalert2';
import { HorasEventualService } from '../../../services/horas-eventual.service';
import { CatalogoHorasEventual, HorasEventual } from '../../../models/horas-eventual.model';

interface DialogData {
  row?: HorasEventual;                       // presente = edición
  catalogo?: CatalogoHorasEventual | null;   // si viene, no se vuelve a pedir
  fechaDefecto?: string;                     // al crear: día propuesto (YYYY-MM-DD)
}

type Opcion = { id: number; nombre: string; [k: string]: any };

@Component({
  selector: 'app-eventual-horas-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule, MatDialogModule,
    MatFormFieldModule, MatInputModule, MatAutocompleteModule, MatButtonModule, MatDatepickerModule,
  ],
  templateUrl: './eventual-horas-dialog.component.html',
  styleUrl: './eventual-horas-dialog.component.css',
})
export class EventualHorasDialogComponent implements OnInit {
  catalogo: CatalogoHorasEventual = { clientes: [], instalaciones: [], puestos: [], eventuales: [] };
  cargando = false;
  guardando = false;
  esEdicion = false;

  // Selectores con búsqueda: mientras se escribe el valor es texto; al elegir, es el objeto.
  eventualCtrl = new FormControl<any>('');
  clienteCtrl = new FormControl<any>('');
  instalacionCtrl = new FormControl<any>('');
  puestoCtrl = new FormControl<any>('');

  // Fecha del servicio (datepicker). Por defecto: el día elegido en la pantalla del módulo;
  // al editar, la del registro. Es la fecha por la que se filtra la lista.
  fecha = '';                  // YYYY-MM-DD (valor inicial)
  fechaServicio: Date | null = null;
  horas: number | null = null;
  horasAdicionales: number | null = 0;
  valorCalculado: number | null = null;   // lo escribe el usuario

  // Cache de filtros (evita recalcular listas largas en cada ciclo de pantalla).
  private cacheFiltro: Record<string, { key: string; res: any[] }> = {};

  constructor(
    private ref: MatDialogRef<EventualHorasDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private srv: HorasEventualService,
  ) {}

  ngOnInit(): void {
    const row = this.data?.row;
    this.esEdicion = !!row?.id;
    this.fecha = row?.fecha || this.data?.fechaDefecto || this.hoy();
    this.fechaServicio = this.aFecha(this.fecha);
    this.horas = row?.horas ?? null;
    this.horasAdicionales = row?.horas_adicionales ?? 0;
    this.valorCalculado = row?.valor_calculado ?? null;
    if (this.data?.catalogo) {
      this.catalogo = this.data.catalogo;
      this.precargar(row);
    } else {
      this.cargando = true;
      this.srv.catalogo().subscribe({
        next: (c) => { this.catalogo = c; this.cargando = false; this.precargar(row); },
        error: () => { this.cargando = false; },
      });
    }
  }

  // ---------- Selección ----------
  private obj(v: any): Opcion | null {
    return v && typeof v === 'object' ? v : null;
  }
  get eventualSel(): Opcion | null { return this.obj(this.eventualCtrl.value); }
  get clienteSel(): Opcion | null { return this.obj(this.clienteCtrl.value); }
  get instalacionSel(): Opcion | null { return this.obj(this.instalacionCtrl.value); }
  get puestoSel(): Opcion | null { return this.obj(this.puestoCtrl.value); }

  // Banco: solo lectura, sale de los datos del eventual (vacío si no lo tiene).
  get banco(): string { return this.eventualSel?.['banco'] || ''; }

  displayOpcion = (o: any): string => (o && typeof o === 'object') ? (o.nombre || '') : (o || '');

  onClienteSel(): void {
    // Cambió el cliente: la instalación y el puesto anteriores ya no aplican.
    this.instalacionCtrl.setValue('');
    this.puestoCtrl.setValue('');
  }

  onInstalacionSel(): void {
    this.puestoCtrl.setValue('');
  }

  limpiar(ctrl: FormControl<any>, ev: Event, cascada?: 'cliente' | 'instalacion'): void {
    ev.stopPropagation();
    ctrl.setValue('');
    if (cascada === 'cliente') { this.onClienteSel(); }
    if (cascada === 'instalacion') { this.onInstalacionSel(); }
  }

  // ---------- Listas filtradas (se escribe para filtrar) ----------
  get eventualesFiltrados(): Opcion[] {
    return this.filtrar('ev', this.catalogo.eventuales, this.eventualCtrl.value,
      (e: any) => `${e.nombre} ${e.cedula}`);
  }

  get clientesFiltrados(): Opcion[] {
    return this.filtrar('cli', this.catalogo.clientes, this.clienteCtrl.value, (c: any) => c.nombre);
  }

  get instalacionesFiltradas(): Opcion[] {
    const c = this.clienteSel;
    if (!c) { return []; }
    const base = this.catalogo.instalaciones.filter(i => i.cliente_id === c.id);
    return this.filtrar(`inst${c.id}`, base, this.instalacionCtrl.value, (i: any) => i.nombre);
  }

  get puestosFiltrados(): Opcion[] {
    const i = this.instalacionSel;
    if (!i) { return []; }
    const base = this.catalogo.puestos.filter(p => p.instalacion_id === i.id);
    return this.filtrar(`pue${i.id}`, base, this.puestoCtrl.value, (p: any) => p.nombre);
  }

  private norm(s: string): string {
    return (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  // Cada palabra escrita debe aparecer (en cualquier orden). Máx. 100 opciones visibles.
  private filtrar(id: string, lista: any[], valor: any, texto: (x: any) => string): Opcion[] {
    const q = typeof valor === 'string' ? this.norm(valor).trim() : '';
    const key = `${lista.length}|${q}`;
    const c = this.cacheFiltro[id];
    if (c && c.key === key) { return c.res; }
    const tokens = q.split(/\s+/).filter(Boolean);
    const res = (tokens.length
      ? lista.filter(x => { const h = this.norm(texto(x)); return tokens.every(t => h.includes(t)); })
      : lista).slice(0, 100);
    this.cacheFiltro[id] = { key, res };
    return res;
  }

  // ---------- Edición: dejar elegidos los valores del registro ----------
  private precargar(row?: HorasEventual): void {
    if (!row) { return; }
    const buscar = (lista: any[], id: any, respaldo: any) =>
      lista.find(x => x.id === id) || (id ? respaldo : null);
    const ev = buscar(this.catalogo.eventuales, row.persona_id,
      { id: row.persona_id, nombre: row.persona || '', cedula: row.cedula || '', banco: row.banco || '' });
    const cli = buscar(this.catalogo.clientes, row.cliente_id, { id: row.cliente_id, nombre: row.cliente || '' });
    const inst = buscar(this.catalogo.instalaciones, row.instalacion_id,
      { id: row.instalacion_id, nombre: row.instalacion || '', cliente_id: row.cliente_id });
    const pue = buscar(this.catalogo.puestos, row.puesto_id,
      { id: row.puesto_id, nombre: row.puesto || '', instalacion_id: row.instalacion_id });
    // Si ya no están en el catálogo (inactivos), se agregan para poder mostrarlos.
    if (ev && !this.catalogo.eventuales.includes(ev)) { this.catalogo.eventuales = [ev, ...this.catalogo.eventuales]; }
    if (inst && !this.catalogo.instalaciones.includes(inst)) { this.catalogo.instalaciones = [inst, ...this.catalogo.instalaciones]; }
    if (pue && !this.catalogo.puestos.includes(pue)) { this.catalogo.puestos = [pue, ...this.catalogo.puestos]; }
    this.eventualCtrl.setValue(ev || '');
    this.clienteCtrl.setValue(cli || '');
    this.instalacionCtrl.setValue(inst || '');
    this.puestoCtrl.setValue(pue || '');
  }

  // ---------- Guardar ----------
  private aviso(text: string): void {
    Swal.fire({ icon: 'warning', title: 'Falta información', text });
  }

  guardar(): void {
    const ev = this.eventualSel;
    const cli = this.clienteSel;
    const inst = this.instalacionSel;
    const pue = this.puestoSel;
    if (!this.fechaServicio) { return this.aviso('Indica la fecha del servicio.'); }
    if (!ev) { return this.aviso('Elige el eventual de la lista.'); }
    if (!cli) { return this.aviso('Elige el cliente de la lista.'); }
    if (!inst) { return this.aviso('Elige la instalación de la lista.'); }
    if (!pue && typeof this.puestoCtrl.value === 'string' && this.puestoCtrl.value.trim()) {
      return this.aviso('Elige el puesto de la lista o déjalo vacío.');
    }
    const h = Number(this.horas);
    if (!Number.isInteger(h) || h < 1 || h > 24) {
      return this.aviso('Las horas trabajadas deben ser un número entero de 1 a 24.');
    }
    const adic = (this.horasAdicionales === null || (this.horasAdicionales as any) === '') ? 0 : Number(this.horasAdicionales);
    if (!Number.isInteger(adic) || adic < 0 || adic > 24) {
      return this.aviso('Las horas adicionales deben ser un número entero de 0 a 24.');
    }
    if (this.valorCalculado === null || (this.valorCalculado as any) === '') {
      return this.aviso('Ingresa el valor calculado.');
    }
    const valor = Number(this.valorCalculado);
    if (!Number.isFinite(valor) || valor < 0) {
      return this.aviso('El valor calculado debe ser un número mayor o igual a 0.');
    }

    const payload: HorasEventual = {
      fecha: this.aTexto(this.fechaServicio),
      persona_id: ev.id,
      cliente_id: cli.id,
      instalacion_id: inst.id,
      puesto_id: pue?.id ?? null,
      horas: h,
      horas_adicionales: adic,
      valor_calculado: valor,
    };
    this.guardando = true;
    const id = this.data?.row?.id;
    const req = (this.esEdicion && id) ? this.srv.actualizar(id, payload) : this.srv.crear(payload);
    req.subscribe({
      next: (res) => this.ref.close(res),
      error: (err) => {
        this.guardando = false;
        Swal.fire({ icon: 'error', title: 'No se pudo guardar', text: err?.error?.error || 'Revisa los datos e intenta de nuevo.' });
      },
    });
  }

  cancelar(): void {
    this.ref.close();
  }

  // 'YYYY-MM-DD' <-> Date en hora LOCAL (sin corrimiento de zona horaria).
  private aFecha(s: string): Date | null {
    const [y, m, d] = (s || '').split('-').map(Number);
    return (y && m && d) ? new Date(y, m - 1, d) : null;
  }

  private aTexto(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  private hoy(): string {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
}
