import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit, ViewChild, ElementRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatIconModule } from '@angular/material/icon';
import { Asignacion, PatronAsignacion } from '../../../models/asignacion.model';
import { Cliente, Persona, Instalacion, Puesto, Horario } from '../../../models';
import { InstalacionService } from '../../../services/instalacion.service';
import { PuestoService } from '../../../services/puesto.service';
import { PersonaService } from '../../../services/persona.service';
import { firstValueFrom } from 'rxjs';
import Swal from 'sweetalert2';

export interface AsignacionFormData {
  asignacion: Asignacion;
  modoEdicion: boolean;
  textoBoton: string;
  clientes: Cliente[];
  personas: Persona[];
  horarios: Horario[];
  patrones: PatronAsignacion[];
  clienteSeleccionado: number | null;
  instalacionSeleccionada: number | null;
  occupiedPuestoIds?: number[];
  occupiedCounts?: { [puestoId: number]: number };
  assignedPersonaIds?: number[];
  patronDetectado?: string;   // patron de turnos detectado (ej. '331'); solo referencia
}

export interface AsignacionFormResult {
  action: 'save' | 'cancel';
  asignacion?: Asignacion;
  clienteSeleccionado?: number | null;
  instalacionSeleccionada?: number | null;
  // Solo en modo NUEVO: ids de las personas a asignar (una asignacion por cada una,
  // hasta el cupo del puesto). Lista vacia = HUECA.
  personaIds?: (number | null)[];
  // Paralelo a personaIds: turno elegido de cada persona ('Diurno'|'Nocturno'|null) para
  // puestos día/noche. null = sin turno específico (el calendario se llena como siempre).
  turnosPreferidos?: (string | null)[];
}

@Component({
  selector: 'app-asignacion-form',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule,
    MatInputModule,
    MatAutocompleteModule,
    MatIconModule
  ],
  templateUrl: './asignacion-form.component.html',
  styleUrl: './asignacion-form.component.css'
})
export class AsignacionFormComponent implements OnInit {
  asignacion: Asignacion;
  modoEdicion: boolean;
  textoBoton: string;

  isSaving = false;

  clientes: Cliente[] = [];
  personas: Persona[] = [];
  horarios: Horario[] = [];
  patrones: PatronAsignacion[] = [];

  instalaciones: Instalacion[] = [];
  puestos: Puesto[] = [];
  puestoSeleccionado: Puesto | null = null;
  puestosFiltrados: Puesto[] = [];
  // Resumen del horario del puesto elegido (turno · días · horas) para mostrarlo
  // al lado de la persona y saber a qué turno se está asignando.
  turnosResumen: { turno: string; dias: string; horas: string }[] = [];
  occupiedPuestoIds = new Set<number>();
  occupiedCounts: { [puestoId: number]: number } = {};
  assignedPersonaIds = new Set<number>();

  personaSeleccionada: Persona | null = null;
  personasFiltradas: Persona[] = [];
  // Modo NUEVO: varias personas a la vez, hasta el cupo del puesto.
  personasSeleccionadas: Persona[] = [];
  // Turno elegido por persona (puestos día/noche): { personaId: 'Diurno'|'Nocturno' }.
  turnoPorPersona: { [id: number]: string } = {};
  @ViewChild('personaInput') personaInputRef?: ElementRef<HTMLInputElement>;

  clienteSeleccionadoObj: Cliente | null = null;
  clientesFiltrados: Cliente[] = [];

  clienteSeleccionado: number | null = null;
  instalacionSeleccionada: number | null = null;

  constructor(
    private dialogRef: MatDialogRef<AsignacionFormComponent, AsignacionFormResult>,
    private instalacionService: InstalacionService,
    private puestoService: PuestoService,
    private personaService: PersonaService,
    @Inject(MAT_DIALOG_DATA) public data: AsignacionFormData
  ) {
    this.asignacion = { ...data.asignacion };
    this.modoEdicion = data.modoEdicion;
    this.textoBoton = data.textoBoton;
    this.clientes = data.clientes || [];
    this.personas = data.personas || [];
    this.horarios = data.horarios || [];
    this.patrones = data.patrones || [];
    this.clienteSeleccionado = data.clienteSeleccionado ?? null;
    this.instalacionSeleccionada = data.instalacionSeleccionada ?? null;
    this.occupiedPuestoIds = new Set(
      (data.occupiedPuestoIds || [])
        .map(id => Number(id))
        .filter(id => Number.isFinite(id) && id > 0)
    );
    this.occupiedCounts = data.occupiedCounts || {};
    this.assignedPersonaIds = new Set(
      (data.assignedPersonaIds || [])
        .map(id => Number(id))
        .filter(id => Number.isFinite(id) && id > 0)
    );
  }

  ngOnInit(): void {
    const today = new Date();
    this.asignacion.start_date = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`;
    this.clientesFiltrados = this.clientes.slice();
    this.setClienteSeleccionadoFromAsignacion();
    this.personasFiltradas = this.getPersonasActivas();
    this.setPersonaSeleccionadaFromAsignacion();
    this.puestosFiltrados = this.puestos.slice();
    this.setPuestoSeleccionadoFromAsignacion();
    if (this.clienteSeleccionado) {
      this.cargarInstalaciones(this.clienteSeleccionado, this.instalacionSeleccionada || undefined, this.asignacion.puesto || undefined);
    }
  }

  forceFirstDayOfMonth(value?: string | null): void {
    const raw = (value ?? this.asignacion.start_date) || '';
    if (!raw) return;
    const parts = raw.split('-').map(Number);
    const year = Number.isFinite(parts[0]) ? parts[0] : new Date().getFullYear();
    const month = Number.isFinite(parts[1]) ? parts[1] : new Date().getMonth() + 1;
    this.asignacion.start_date = `${year}-${String(month).padStart(2, '0')}-01`;
  }
  
  onClientChange(): void {
    if (!this.clienteSeleccionado) {
      this.instalaciones = [];
      this.puestos = [];
      this.puestosFiltrados = [];
      this.puestoSeleccionado = null;
      this.instalacionSeleccionada = null;
      this.asignacion.cliente = 0;
      this.asignacion.instalacion = 0;
      this.asignacion.puesto = 0;
      return;
    }
    this.asignacion.cliente = this.clienteSeleccionado;
    this.instalacionSeleccionada = null;
    this.asignacion.instalacion = 0;
    this.asignacion.puesto = 0;
    this.instalaciones = [];
    this.puestos = [];
    this.puestosFiltrados = [];
    this.puestoSeleccionado = null;
    this.personaSeleccionada = null;
    this.asignacion.persona = 0;
    this.personasSeleccionadas = [];
    this.personasFiltradas = this.getPersonasActivas();
    this.cargarInstalaciones(this.clienteSeleccionado);
  }

  filtrarPuestos(value: string): void {
    const term = (value || '').trim().toLowerCase();
    this.puestosFiltrados = this.puestos.filter(p => {
      if (!term) return true;
      const nombre = (p.nombre || '').toLowerCase();
      return nombre.includes(term);
    });
  }

  displayPuestoLabel = (puesto: Puesto | null): string => {
    if (!puesto) return '';
    const horas = this.getPuestoHoras(puesto);
    return horas ? `${puesto.nombre} - ${horas}` : (puesto.nombre || '');
  };

  getPuestoHoras(puesto: Puesto | null | undefined): string {
    if (!puesto) return '';

    const fromHorarios = Array.isArray(puesto.horarios)
      ? Array.from(new Set((puesto.horarios || [])
          .map(h => Number((h as any)?.horas || 0))
          .filter(h => h > 0)))
          .sort((a, b) => a - b)
      : [];

    if (fromHorarios.length > 0) {
      return fromHorarios.length === 1
        ? `${fromHorarios[0]} horas`
        : `${fromHorarios.join(' / ')} horas`;
    }

    const direct = Number((puesto as any).horas_trabajo || 0);
    if (direct > 0) return `${direct} horas`;

    const resumen = String((puesto as any).resumen || '').trim();
    const match = resumen.match(/\b(\d{1,2})\b/);
    if (match) {
      const val = Number(match[1]);
      if (val > 0) return `${val} horas`;
    }

    return '';
  }

  isPuestoOcupado(puestoId: number | null | undefined): boolean {
    if (!puestoId) return false;
    const puesto = this.puestos.find(p => p.id === Number(puestoId));
    // Lleno = cupos ocupados alcanzan la capacidad del puesto.
    return this.getPuestoOcupadas(puestoId) >= this.getPuestoCapacidad(puesto);
  }

  // Capacidad (cupos) del puesto.
  getPuestoCapacidad(puesto: Puesto | null | undefined): number {
    const cap = Number((puesto as any)?.cantidad_puestos);
    return Number.isFinite(cap) && cap > 0 ? cap : 1;
  }

  // Cupos ya ocupados de un puesto en el mes.
  getPuestoOcupadas(puestoId: number | null | undefined): number {
    const n = Number(this.occupiedCounts?.[Number(puestoId)]);
    return Number.isFinite(n) && n > 0 ? n : 0;
  }

  // Texto "(ocupadas/capacidad)" para mostrar junto al ícono.
  getPuestoCupoLabel(puesto: Puesto | null | undefined): string {
    return `${this.getPuestoOcupadas(puesto?.id)}/${this.getPuestoCapacidad(puesto)}`;
  }

  seleccionarPuesto(puesto: Puesto): void {
    this.puestoSeleccionado = puesto || null;
    this.asignacion.puesto = puesto?.id || 0;
    // Cambió el puesto -> cambia el cupo: reiniciar personas marcadas.
    this.personasSeleccionadas = [];
    this.turnoPorPersona = {};
    this.personaSeleccionada = null;
    this.asignacion.persona = 0;
    this.personasFiltradas = this.getPersonasActivas();
    this.computeTurnosResumen();
    // Auto-rellenar el horario desde el puesto si lo tiene
    const horarioPuesto = (puesto as any)?.horario;
    if (horarioPuesto) {
      this.asignacion.horario = horarioPuesto;
    }
  }

  // Resumen legible del horario del puesto agrupado por turno (turno · días · horas),
  // p.ej. "Diurno · L M X J V S D · 07:00-19:00". Se muestra al elegir la persona.
  private computeTurnosResumen(): void {
    const hs = ((this.puestoSeleccionado as any)?.horarios || []) as any[];
    if (!Array.isArray(hs) || !hs.length) { this.turnosResumen = []; return; }
    const letras = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
    const groups: { [k: string]: { turno: string; ing: string; sal: string; dias: number[] } } = {};
    for (const h of hs) {
      const turno = (h?.turno || 'Diurno').toString();
      const ing = this.fmtHora(h?.hora_ingreso, turno, 'ing');
      const sal = this.fmtHora(h?.hora_salida, turno, 'sal');
      const key = `${turno}|${ing}|${sal}`;
      if (!groups[key]) groups[key] = { turno, ing, sal, dias: [] };
      const d = Number(h?.dia);
      if (d >= 1 && d <= 7) groups[key].dias.push(d);
    }
    // Ordenar: Diurno, Nocturno, 24, otros
    const orden: { [t: string]: number } = { 'Diurno': 0, 'Nocturno': 1, '24': 2 };
    this.turnosResumen = Object.values(groups)
      .sort((a, b) => (orden[a.turno] ?? 9) - (orden[b.turno] ?? 9))
      .map(g => ({
        turno: g.turno,
        dias: Array.from(new Set(g.dias)).sort((a, b) => a - b).map(d => letras[d - 1]).join(' '),
        horas: (g.ing && g.sal) ? `${g.ing}-${g.sal}` : '',
      }));
  }

  // Formatea "07:00:00" -> "07:00"; si viene vacío usa el default del turno.
  private fmtHora(v: any, turno?: string, tipo?: 'ing' | 'sal'): string {
    const s = (v ?? '').toString().trim();
    const m = s.match(/^(\d{1,2}):(\d{2})/);
    if (m) return `${m[1].padStart(2, '0')}:${m[2]}`;
    const t = (turno || '').toLowerCase();
    if (t.startsWith('n')) return tipo === 'ing' ? '19:00' : '07:00';
    if (t.startsWith('d')) return tipo === 'ing' ? '07:00' : '19:00';
    if (t.startsWith('2')) return '07:00';
    return '';
  }

  // Solo lectura si el puesto ya tiene horario; editable si no (se guardará en el puesto al asignar).
  puestoTieneHorario(): boolean {
    return !!(this.puestoSeleccionado as any)?.horario;
  }

  private setPuestoSeleccionadoFromAsignacion(): void {
    if (!this.asignacion.puesto) {
      this.puestoSeleccionado = null;
      this.turnosResumen = [];
      return;
    }
    this.puestoSeleccionado = this.puestos.find(p => p.id === this.asignacion.puesto) || null;
    this.computeTurnosResumen();
  }

  filtrarClientes(value: string): void {
    const term = (value || '').trim().toLowerCase();
    this.clientesFiltrados = this.clientes.filter(cliente => {
      if (!term) return true;
      const nombre = (cliente.nombre_comercial || '').toLowerCase();
      return nombre.includes(term);
    });
  }

  displayClienteLabel = (cliente: Cliente | null): string => {
    return cliente?.nombre_comercial || '';
  };

  seleccionarCliente(cliente: Cliente): void {
    this.clienteSeleccionado = cliente?.id ?? null;
    this.clienteSeleccionadoObj = cliente || null;
    this.onClientChange();
  }

  // Limpia el buscador de Cliente (la X): borra texto, selección y todo en cascada.
  limpiarCliente(inputEl: HTMLInputElement): void {
    if (inputEl) { inputEl.value = ''; }
    this.clienteSeleccionadoObj = null;
    this.clienteSeleccionado = null;
    this.clientesFiltrados = this.clientes.slice();
    this.onClientChange();
  }

  private setClienteSeleccionadoFromAsignacion(): void {
    if (!this.clienteSeleccionado) return;
    this.clienteSeleccionadoObj = this.clientes.find(c => c.id === this.clienteSeleccionado) || null;
  }

  isPersonaAssigned(persona: Persona): boolean {
    if (!persona?.id) return false;
    if (this.personaSeleccionada?.id === persona.id) return false;
    return this.assignedPersonaIds.has(Number(persona.id));
  }

  formatPersonaLabel(persona: Persona): string {
    const apellidos = persona.apellidos || '';
    const nombres = persona.nombres || '';
    const tipo = persona.tipo ? ` (${persona.tipo})` : '';
    return `${apellidos} ${nombres}`.trim() + tipo;
  }

  getPersonasActivas(): Persona[] {
    // Todos los tipos EXCEPTO sacavacaciones (sacafranco SÍ aparece), sin filtrar
    // por provincia/cantón (se muestran todas y se indica su ubicación con un badge).
    const yaMarcadas = new Set(this.personasSeleccionadas.map(p => p.id));
    return this.personas.filter(persona => {
      const tipo = (persona.tipo || '').toString().toUpperCase();
      if (persona.is_active === false) return false;
      if (tipo === 'SACAVACACIONES') return false;
      if (yaMarcadas.has(persona.id)) return false;   // ya seleccionada (multi)
      return true;
    });
  }

  getProvinciaCanton(persona: Persona): string {
    const prov = ((persona as any)?.provincia_nombre || '').toString().trim();
    const cant = ((persona as any)?.canton_nombre || '').toString().trim();
    if (prov && cant) return `${prov} - ${cant}`;
    return prov || cant || '';
  }

  private getProvinciaIdFromInstalacion(): number | null {
    const instId = this.instalacionSeleccionada;
    if (!instId) return null;
    const inst = this.instalaciones.find(i => i.id === instId);
    return (inst as any)?.provincia_id || (inst as any)?.provincia || null;
  }

  private getCantonIdFromInstalacion(): number | null {
    const instId = this.instalacionSeleccionada;
    if (!instId) return null;
    const inst = this.instalaciones.find(i => i.id === instId);
    return (inst as any)?.canton_id || (inst as any)?.canton || null;
  }

  canSelectPersona(): boolean {
    return !!this.clienteSeleccionado
      && !!this.instalacionSeleccionada
      && !!this.asignacion.puesto;
  }

  // Cupos LIBRES del puesto en el mes = capacidad - ya ocupados.
  cuposDisponibles(): number {
    const cap = this.getPuestoCapacidad(this.puestoSeleccionado);
    const ocup = this.getPuestoOcupadas(this.asignacion.puesto);
    return Math.max(0, cap - ocup);
  }

  // Selección múltiple SOLO en modo NUEVO y cuando quedan 2+ cupos libres.
  multiPersona(): boolean {
    return !this.modoEdicion && this.cuposDisponibles() > 1;
  }

  // ¿Ya se llenaron los cupos con las personas marcadas?
  cuposLlenos(): boolean {
    return this.personasSeleccionadas.length >= this.cuposDisponibles();
  }

  quitarPersonaSel(p: Persona): void {
    this.personasSeleccionadas = this.personasSeleccionadas.filter(x => x.id !== p.id);
    if (p?.id) { delete this.turnoPorPersona[p.id]; }
    this.personasFiltradas = this.getPersonasActivas();
  }

  // Turnos que ofrece el puesto elegido (para el selector por persona).
  getTurnosDisponibles(): string[] {
    return Array.from(new Set(this.turnosResumen.map(t => t.turno)));
  }

  // Mostrar el selector de turno por persona solo si el puesto tiene 2+ turnos (día y noche).
  hasTurnoSelector(): boolean {
    return !this.modoEdicion && this.getTurnosDisponibles().length >= 2;
  }

  // Horas "07:00-19:00" de un turno, para mostrarlas junto al nombre.
  turnoHoras(turno: string): string {
    const t = this.turnosResumen.find(x => x.turno === turno);
    return t?.horas || '';
  }

  setTurnoPersona(p: Persona, turno: string): void {
    if (!p?.id) return;
    this.turnoPorPersona[p.id] = turno;
    // Día/noche con 2 personas y 2 turnos: al elegir uno, la otra persona toma el
    // turno contrario automáticamente (una diurna y otra nocturna).
    const turnos = this.getTurnosDisponibles();
    if (turnos.length === 2 && this.personasSeleccionadas.length === 2) {
      const otra = this.personasSeleccionadas.find(x => x.id !== p.id);
      const otroTurno = turnos.find(t => t !== turno);
      if (otra?.id && otroTurno) {
        this.turnoPorPersona[otra.id] = otroTurno;
      }
    }
  }

  // Turno por defecto al agregar una persona: reparte en orden (1ª Diurno, 2ª Nocturno...).
  private defaultTurnoParaNueva(): string {
    const turnos = this.getTurnosDisponibles();
    if (!turnos.length) return '';
    if (turnos.length < 2) return turnos[0];
    return turnos[this.personasSeleccionadas.length % turnos.length];
  }

  filtrarPersonas(value: string): void {
    const term = (value || '').trim().toLowerCase();
    const tokens = term.split(/\s+/).filter(Boolean);
    this.personasFiltradas = this.getPersonasActivas().filter(persona => {
      if (!tokens.length) return true;
      // Coincide si cada palabra escrita está en "nombres apellidos cédula" (cualquier orden).
      const hay = `${persona.nombres || ''} ${persona.apellidos || ''} ${persona.cedula || ''}`.toLowerCase();
      return tokens.every(t => hay.includes(t));
    });
  }

  displayPersonaLabel = (persona: Persona | null): string => {
    if (!persona) return '';
    const apellidos = persona.apellidos || '';
    const nombres = persona.nombres || '';
    return `${apellidos} ${nombres}`.trim();
  };

  seleccionarPersona(persona: Persona): void {
    if (this.multiPersona()) {
      // Agregar a la lista (hasta el cupo), sin repetir, y limpiar el buscador.
      if (persona?.id
          && !this.personasSeleccionadas.some(p => p.id === persona.id)
          && this.personasSeleccionadas.length < this.cuposDisponibles()) {
        const turnoDef = this.defaultTurnoParaNueva();
        this.personasSeleccionadas = [...this.personasSeleccionadas, persona];
        if (turnoDef) { this.turnoPorPersona[persona.id] = turnoDef; }
      }
      this.personaSeleccionada = null;
      if (this.personaInputRef?.nativeElement) { this.personaInputRef.nativeElement.value = ''; }
      this.personasFiltradas = this.getPersonasActivas();
      return;
    }
    this.asignacion.persona = persona?.id || 0;
    this.personaSeleccionada = persona || null;
  }

  // Limpia el buscador de Persona (la X): borra texto y selección.
  limpiarPersona(inputEl: HTMLInputElement): void {
    if (inputEl) { inputEl.value = ''; }
    this.personaSeleccionada = null;
    this.asignacion.persona = 0;
    this.personasFiltradas = this.getPersonasActivas();
  }

  private setPersonaSeleccionadaFromAsignacion(): void {
    if (!this.asignacion.persona) return;
    this.personaSeleccionada = this.personas.find(p => p.id === this.asignacion.persona) || null;
  }


  onInstalacionChange(): void {
    if (!this.instalacionSeleccionada) {
      this.asignacion.instalacion = 0;
      this.asignacion.puesto = 0;
      this.puestos = [];
      this.puestosFiltrados = [];
      this.puestoSeleccionado = null;
      this.personaSeleccionada = null;
      this.asignacion.persona = 0;
      this.personasFiltradas = this.getPersonasActivas();
      return;
    }
    this.asignacion.instalacion = this.instalacionSeleccionada;
    this.asignacion.puesto = 0;
    this.puestos = [];
    this.puestosFiltrados = [];
    this.puestoSeleccionado = null;
    this.personaSeleccionada = null;
    this.asignacion.persona = 0;
    this.personasSeleccionadas = [];
    this.personasFiltradas = this.getPersonasActivas();
    this.cargarPuestos(this.instalacionSeleccionada);
  }

  private cargarInstalaciones(clienteId: number, preselectInstalacionId?: number, preselectPuestoId?: number): void {
    this.instalacionService.getInstalaciones({ cliente_id: clienteId }).subscribe({
      next: data => {
        this.instalaciones = data || [];
        if (preselectInstalacionId) {
          this.instalacionSeleccionada = preselectInstalacionId;
          this.asignacion.instalacion = preselectInstalacionId;
          this.cargarPuestos(preselectInstalacionId, preselectPuestoId);
          this.personasFiltradas = this.getPersonasActivas();
        }
      },
      error: err => console.error('Error al cargar instalaciones', err)
    });
  }

  private cargarPuestos(instalacionId: number, preselectPuestoId?: number): void {
    this.puestoService.getPuestosPorInstalacion(instalacionId).subscribe({
      next: data => {
        this.puestos = data || [];
        this.puestosFiltrados = this.puestos.slice();
        if (preselectPuestoId) {
          this.asignacion.puesto = preselectPuestoId;
        }
        this.setPuestoSeleccionadoFromAsignacion();
      },
      error: err => console.error('Error al cargar puestos', err)
    });
  }

  onCancel(): void {
    this.dialogRef.close({ action: 'cancel' });
  }

  isFormValid(): boolean {
    // El horario ya no se pide en el modal: proviene del puesto (PuestoHorario).
    // La PERSONA es opcional: sin persona se crea una HUECA (puesto sin guardia).
    return !!this.clienteSeleccionado
      && !!this.instalacionSeleccionada
      && !!this.asignacion.puesto
      && !!this.asignacion.start_date;
    }

  async onSave(): Promise<void> {
    if (!this.isFormValid() || this.isSaving) return;

    // Modo NUEVO con varios cupos: devolver la lista de personas marcadas (una
    // asignacion por cada una). Se omite el prompt de SACAFRANCO->FIJOS aqui.
    if (this.multiPersona()) {
      this.isSaving = true;
      this.dialogRef.close({
        action: 'save',
        asignacion: this.asignacion,
        clienteSeleccionado: this.clienteSeleccionado,
        instalacionSeleccionada: this.instalacionSeleccionada,
        personaIds: this.personasSeleccionadas.map(p => p.id as number),
        turnosPreferidos: this.personasSeleccionadas.map(
          p => this.hasTurnoSelector() ? (this.turnoPorPersona[p.id as number] || null) : null
        ),
      });
      return;
    }

    // Si la persona es SACAFRANCO y se la asigna a un puesto fijo, ofrecer cambiar su tipo a FIJOS.
    const persona = this.personaSeleccionada;
    const esSacafranco = (persona?.tipo || '').toString().toUpperCase() === 'SACAFRANCO';
    if (esSacafranco && persona?.id) {
      const nombre = `${persona.apellidos || ''} ${persona.nombres || ''}`.trim();
      const res = await Swal.fire({
        icon: 'question',
        title: '¿Cambiar tipo a FIJOS?',
        html: `<b>${nombre}</b> es <b>SACAFRANCO</b> y lo estás asignando a un puesto fijo.<br>¿Deseas cambiar su tipo a <b>FIJOS</b>?`,
        showCancelButton: true,
        confirmButtonText: 'Sí, cambiar a FIJOS',
        cancelButtonText: 'No, dejar SACAFRANCO',
        confirmButtonColor: '#0d6efd',
      });
      if (res.isConfirmed) {
        this.isSaving = true;
        try {
          await firstValueFrom(this.personaService.cambiarTipo(persona.id, 'FIJOS'));
          persona.tipo = 'FIJOS';
        } catch {
          // Si falla el cambio de tipo, avisar pero continuar: la asignación se guarda igual.
          await Swal.fire({
            icon: 'warning',
            title: 'No se pudo cambiar el tipo',
            text: 'La asignación se guardará igual; el tipo quedó como SACAFRANCO.',
          });
        }
        this.isSaving = false;
      }
    }

    // Sin persona -> es una HUECA (puesto sin guardia).
    this.asignacion.es_hueca = !this.asignacion.persona;

    this.isSaving = true;
    this.dialogRef.close({
      action: 'save',
      asignacion: this.asignacion,
      clienteSeleccionado: this.clienteSeleccionado,
      instalacionSeleccionada: this.instalacionSeleccionada,
      // Modo NUEVO: una persona (o ninguna = hueca). En EDICION no se envia.
      personaIds: this.modoEdicion ? undefined : (this.asignacion.persona ? [this.asignacion.persona] : []),
    });
  }

  openStartDatePicker(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    if (!input) return;
    if (typeof input.showPicker === 'function') {
      input.showPicker();
    } else {
      input.focus();
    }
  }
}
