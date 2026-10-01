import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatSelectModule } from '@angular/material/select';
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
    MatFormFieldModule, MatInputModule, MatAutocompleteModule, MatButtonModule, MatDatepickerModule, MatSelectModule,
  ],
  templateUrl: './eventual-horas-dialog.component.html',
  styleUrl: './eventual-horas-dialog.component.css',
})
export class EventualHorasDialogComponent implements OnInit {
  catalogo: CatalogoHorasEventual = { clientes: [], instalaciones: [], puestos: [], eventuales: [], tarifas: [] };
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
  horasSolicitadas: number | null = null;
  horas: number | null = null;             // horas trabajadas
  bonificacion: number | null = null;      // opcional
  // Horas adicionales: se llenan con trabajadas - solicitadas y se pueden cambiar a mano.
  horasAdic: number | null = null;
  adicManual = false;
  // Valor calculado: se llena solo (tarifa + bonificación) y se puede corregir a mano.
  valorCalculado: number | null = null;
  valorManual = false;                     // true = el usuario lo corrigió
  // Rango de horas (tramo de la tarifa): se marca solo según las horas; se puede cambiar.
  tarifaSel: number | null = null;

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
    this.horasSolicitadas = row?.horas_solicitadas ?? null;
    this.horas = row?.horas ?? null;
    this.bonificacion = row?.bonificacion ?? null;
    this.bonoAnterior = Number(this.bonificacion) || 0;
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

  // Texto escrito que NO se eligió de la lista (se guarda tal cual, solo en este registro).
  private libre(ctrl: FormControl<any>): string {
    const v = ctrl.value;
    return typeof v === 'string' ? v.trim() : '';
  }
  get clienteLibre(): boolean { return !this.clienteSel && !!this.libre(this.clienteCtrl); }
  get instalacionLibre(): boolean { return !this.instalacionSel && !!this.libre(this.instalacionCtrl); }
  get puestoLibre(): boolean { return !this.puestoSel && !!this.libre(this.puestoCtrl); }

  // Banco: solo lectura, sale de los datos del eventual (vacío si no lo tiene).
  get banco(): string { return this.eventualSel?.['banco'] || ''; }
  get cedula(): string { return this.eventualSel?.['cedula'] || ''; }
  get tipoCuenta(): string { return this.eventualSel?.['tipo_cuenta'] || ''; }
  get numeroCuenta(): string { return this.eventualSel?.['numero_cuenta'] || ''; }

  // ---------- Cálculos (solo lectura; el servidor los recalcula al guardar) ----------
  // Horas adicionales sugeridas = trabajadas - solicitadas (mínimo 0).
  get horasAdicionales(): number {
    return Math.max(0, (Number(this.horas) || 0) - (Number(this.horasSolicitadas) || 0));
  }

  // Horas para el rango de la tarifa: las HORAS TRABAJADAS
  // (ej. 11 trabajadas -> 10-12 h; 8 trabajadas -> 7-9 h).
  get horasTarifa(): number {
    return Number(this.horas) || 0;
  }

  // Tramo que corresponde por la regla (el que se marca solo).
  get tramoAuto(): { id: number; horas_min: number; horas_max: number; valor: number } | null {
    const h = this.horasTarifa;
    if (!h) { return null; }
    return (this.catalogo.tarifas || []).find(t => h >= t.horas_min && h <= t.horas_max) || null;
  }

  // Tramo elegido en "Rango de horas".
  private get tramo(): { id: number; horas_min: number; horas_max: number; valor: number } | null {
    return (this.catalogo.tarifas || []).find(t => t.id === this.tarifaSel) || null;
  }

  // Cambiaron las horas: el rango se vuelve a marcar solo y el valor se recalcula.
  onHorasChange(): void {
    this.tarifaSel = this.tramoAuto?.id ?? null;
    if (!this.adicManual) { this.horasAdic = this.horasAdicionales; }
    this.recalcular();
  }

  // El usuario escribe las horas adicionales (si las borra, vuelven a calcularse solas).
  onAdicEditado(v: any): void {
    if (v === null || v === undefined || v === '') {
      this.adicManual = false;
      this.horasAdic = this.horasAdicionales;
      return;
    }
    this.horasAdic = Number(v);
    this.adicManual = this.horasAdic !== this.horasAdicionales;
  }

  // El usuario eligió otro rango a mano.
  onRangoChange(): void {
    this.recalcular();
  }

  // ¿El rango elegido es distinto al que corresponde por las horas?
  get rangoCambiado(): boolean {
    return !!this.tarifaSel && this.tarifaSel !== (this.tramoAuto?.id ?? null);
  }

  get valorTarifa(): number { return this.tramo?.valor ?? 0; }

  get montoBonificacion(): number { return Number(this.bonificacion) || 0; }

  // Valor sugerido = tarifa del tramo (ver horasTarifa) + bonificación.
  get valorSugerido(): number { return this.redondear(this.valorTarifa + this.montoBonificacion); }

  private redondear(v: any): number { return Math.round((Number(v) || 0) * 100) / 100; }

  // Al cambiar horas o bonificación: si el valor no fue corregido a mano, sigue al sugerido.
  recalcular(): void {
    if (this.valorManual) { return; }
    const sinHoras = this.horas === null || (this.horas as any) === '';
    this.valorCalculado = sinHoras ? null : this.valorSugerido;
  }

  // El usuario escribe en "Valor calculado": queda como corrección a mano (si lo borra,
  // vuelve a calcularse solo).
  onValorEditado(v: any): void {
    if (v === null || v === undefined || v === '') {
      this.valorManual = false;
      this.recalcular();
      return;
    }
    this.valorCalculado = Number(v);
    this.valorManual = this.redondear(v) !== this.valorSugerido;
  }

  // Cambió la bonificación: se suma (o resta la diferencia) también cuando el valor fue
  // corregido a mano. Ej. corregido 31.64 + bono 50 -> 81.64.
  private bonoAnterior = 0;
  onBonificacionCambio(): void {
    const nuevo = this.montoBonificacion;
    const ajustado = this.valorManual && this.valorCalculado !== null
      ? this.redondear(Number(this.valorCalculado) + nuevo - this.bonoAnterior) : null;
    if (ajustado !== null && ajustado >= 0) {
      this.valorCalculado = ajustado;
      this.valorManual = this.valorCalculado !== this.valorSugerido;
    } else {
      // Nunca negativo (ej. registro guardado antes, cuyo valor no incluía el bono):
      // vuelve al sugerido = rango + bonificación.
      this.valorManual = false;
      this.recalcular();
    }
    this.bonoAnterior = nuevo;
  }

  usarSugerido(): void {
    this.valorManual = false;
    this.recalcular();
  }

  // Hay horas pero ningún rango elegido (ningún tramo las cubre).
  get sinTramo(): boolean { return this.horasTarifa > 0 && !this.tramo; }

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
      { id: row.persona_id, nombre: row.persona || '', cedula: row.cedula || '', banco: row.banco || '',
        banco_codigo: row.banco_codigo || '', tipo_cuenta: row.tipo_cuenta || '', numero_cuenta: row.numero_cuenta || '' });
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
    // Si se escribieron a mano (no estaban en la lista), se muestra el texto guardado.
    this.clienteCtrl.setValue(row.cliente_libre ? (row.cliente || '') : (cli || ''));
    this.instalacionCtrl.setValue(row.instalacion_libre ? (row.instalacion || '') : (inst || ''));
    this.puestoCtrl.setValue(row.puesto_libre ? (row.puesto || '') : (pue || ''));
    // Horas adicionales guardadas (si difieren de trabajadas - solicitadas, se cambiaron a mano).
    this.horasAdic = row.horas_adicionales ?? this.horasAdicionales;
    this.adicManual = this.horasAdic !== this.horasAdicionales;
    // Rango guardado ("10-12 h"); si no se encuentra, el que corresponde por las horas.
    const guardado = (this.catalogo.tarifas || []).find(t => `${t.horas_min}-${t.horas_max} h` === row.rango_horas);
    this.tarifaSel = guardado?.id ?? this.tramoAuto?.id ?? null;
    // Valor: si se había corregido a mano, se respeta; si no, se carga primero el calculado
    // (rango + bonificación). En ambos casos se puede editar.
    this.valorManual = !!row.valor_manual;
    this.valorCalculado = this.valorManual ? (row.valor_calculado ?? null) : this.valorSugerido;
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
    if (!this.fechaServicio) { return this.aviso('Indica la fecha en Creado.'); }
    if (!ev) { return this.aviso('Elige el eventual de la lista.'); }
    // Cliente / instalación / puesto: de la lista o escritos a mano (no se crean en el sistema).
    const cliTxt = cli ? '' : this.libre(this.clienteCtrl);
    if (!cli && !cliTxt) { return this.aviso('Indica el cliente: elígelo de la lista o escríbelo.'); }
    // Una instalación de la lista solo vale si es de ese cliente; si no, se guarda su nombre.
    const instObj = (inst && cli && inst['cliente_id'] === cli.id) ? inst : null;
    const instTxt = instObj ? '' : (inst ? inst.nombre : this.libre(this.instalacionCtrl));
    if (!instObj && !instTxt) { return this.aviso('Indica la instalación: elígela de la lista o escríbela.'); }
    const pueObj = (pue && instObj && pue['instalacion_id'] === instObj.id) ? pue : null;
    const pueTxt = pueObj ? '' : (pue ? pue.nombre : this.libre(this.puestoCtrl));
    if (!pueObj && !pueTxt) { return this.aviso('Indica el nombre del puesto: elígelo de la lista o escríbelo.'); }
    const vacio = (v: any) => v === null || v === undefined || v === '';
    if (vacio(this.horasSolicitadas)) { return this.aviso('Indica las horas solicitadas.'); }
    const sol = Number(this.horasSolicitadas);
    if (!Number.isInteger(sol) || sol < 0 || sol > 24) {
      return this.aviso('Las horas solicitadas deben ser un número entero de 0 a 24.');
    }
    const h = Number(this.horas);
    if (!Number.isInteger(h) || h < 1 || h > 24) {
      return this.aviso('Las horas trabajadas deben ser un número entero de 1 a 24.');
    }
    const adic = vacio(this.horasAdic) ? null : Number(this.horasAdic);
    if (adic !== null && (!Number.isInteger(adic) || adic < 0 || adic > 24)) {
      return this.aviso('Las horas adicionales deben ser un número entero de 0 a 24.');
    }
    const bono = vacio(this.bonificacion) ? null : Number(this.bonificacion);
    if (bono !== null && (!Number.isFinite(bono) || bono < 0)) {
      return this.aviso('La bonificación debe ser un número mayor o igual a 0.');
    }
    // Vacío = que el servidor lo calcule (tarifa + bonificación).
    const valor = vacio(this.valorCalculado) ? null : Number(this.valorCalculado);
    if (valor !== null && (!Number.isFinite(valor) || valor < 0)) {
      return this.aviso('El valor calculado debe ser un número mayor o igual a 0.');
    }

    const payload: HorasEventual = {
      fecha: this.aTexto(this.fechaServicio),
      persona_id: ev.id,
      cliente_id: cli?.id ?? null,
      cliente_texto: cliTxt,
      instalacion_id: instObj?.id ?? null,
      instalacion_texto: instTxt,
      puesto_id: pueObj?.id ?? null,
      puesto_texto: pueTxt,
      horas_solicitadas: sol,
      horas: h,
      horas_adicionales: adic ?? undefined,
      bonificacion: bono,
      valor_calculado: valor ?? undefined,
      valor_manual: this.valorManual,
      tarifa_id: this.tarifaSel ?? undefined,
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
