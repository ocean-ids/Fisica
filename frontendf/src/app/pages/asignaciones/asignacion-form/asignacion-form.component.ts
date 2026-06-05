import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { Asignacion, PatronAsignacion } from '../../../models/asignacion.model';
import { Cliente, Persona, Instalacion, Puesto, Horario } from '../../../models';
import { InstalacionService } from '../../../services/instalacion.service';
import { PuestoService } from '../../../services/puesto.service';

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
  assignedPersonaIds?: number[];
}

export interface AsignacionFormResult {
  action: 'save' | 'cancel';
  asignacion?: Asignacion;
  clienteSeleccionado?: number | null;
  instalacionSeleccionada?: number | null;
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
    MatAutocompleteModule
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
  occupiedPuestoIds = new Set<number>();
  assignedPersonaIds = new Set<number>();

  personaSeleccionada: Persona | null = null;
  personasFiltradas: Persona[] = [];

  clienteSeleccionadoObj: Cliente | null = null;
  clientesFiltrados: Cliente[] = [];

  clienteSeleccionado: number | null = null;
  instalacionSeleccionada: number | null = null;

  constructor(
    private dialogRef: MatDialogRef<AsignacionFormComponent, AsignacionFormResult>,
    private instalacionService: InstalacionService,
    private puestoService: PuestoService,
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
    return !!puestoId && this.occupiedPuestoIds.has(Number(puestoId));
  }

  seleccionarPuesto(puesto: Puesto): void {
    this.puestoSeleccionado = puesto || null;
    this.asignacion.puesto = puesto?.id || 0;
  }

  private setPuestoSeleccionadoFromAsignacion(): void {
    if (!this.asignacion.puesto) {
      this.puestoSeleccionado = null;
      return;
    }
    this.puestoSeleccionado = this.puestos.find(p => p.id === this.asignacion.puesto) || null;
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
    const provinciaId = this.getProvinciaIdFromInstalacion();
    const cantonId = this.getCantonIdFromInstalacion();

    const tiposPermitidos = new Set([
      'FIJOS',
      'SUPERVISOR MOTORIZADO',
      'SUPERVISOR ZONAL',
    ]);

    return this.personas.filter(persona => {
      const tipo = (persona.tipo || '').toString().toUpperCase();
      if (persona.is_active === false || !tiposPermitidos.has(tipo)) return false;

      if (provinciaId && persona.provincia && persona.provincia !== provinciaId) return false;
      if (cantonId && persona.canton && persona.canton !== cantonId) return false;

      return true;
    });
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

  filtrarPersonas(value: string): void {
    const term = (value || '').trim().toLowerCase();
    this.personasFiltradas = this.getPersonasActivas().filter(persona => {
      if (!term) return true;
      const full = `${persona.apellidos || ''} ${persona.nombres || ''}`.toLowerCase();
      return full.includes(term);
    });
  }

  displayPersonaLabel = (persona: Persona | null): string => {
    if (!persona) return '';
    const apellidos = persona.apellidos || '';
    const nombres = persona.nombres || '';
    return `${apellidos} ${nombres}`.trim();
  };

  seleccionarPersona(persona: Persona): void {
    this.asignacion.persona = persona?.id || 0;
    this.personaSeleccionada = persona || null;
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
    return !!this.clienteSeleccionado
      && !!this.instalacionSeleccionada
      && !!this.asignacion.puesto
      && !!this.asignacion.persona
      && !!this.asignacion.horario
      && !!this.asignacion.start_date;
    }

  onSave(): void {
    if (!this.isFormValid() || this.isSaving) return;
    this.isSaving = true;
    this.dialogRef.close({
      action: 'save',
      asignacion: this.asignacion,
      clienteSeleccionado: this.clienteSeleccionado,
      instalacionSeleccionada: this.instalacionSeleccionada
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
