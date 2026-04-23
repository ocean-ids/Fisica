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

  clientes: Cliente[] = [];
  personas: Persona[] = [];
  horarios: Horario[] = [];
  patrones: PatronAsignacion[] = [];

  instalaciones: Instalacion[] = [];
  puestos: Puesto[] = [];

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
  }

  ngOnInit(): void {
    if (!this.asignacion.start_date) {
      const today = new Date();
      this.asignacion.start_date = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`;
    }
    this.clientesFiltrados = this.clientes.slice();
    this.setClienteSeleccionadoFromAsignacion();
    this.personasFiltradas = this.getPersonasActivas();
    this.setPersonaSeleccionadaFromAsignacion();
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
    this.personaSeleccionada = null;
    this.asignacion.persona = 0;
    this.personasFiltradas = this.getPersonasActivas();
    this.cargarInstalaciones(this.clienteSeleccionado);
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

  formatPersonaLabel(persona: Persona): string {
    const apellidos = persona.apellidos || '';
    const nombres = persona.nombres || '';
    const tipo = persona.tipo ? ` (${persona.tipo})` : '';
    return `${apellidos} ${nombres}`.trim() + tipo;
  }

  getPersonasActivas(): Persona[] {
    const provinciaId = this.getProvinciaIdFromInstalacion();

    return this.personas.filter(persona => {
      const tipo = (persona.tipo || '').toString().toUpperCase();
      if (persona.is_active === false || tipo !== 'FIJOS') return false;

      if (provinciaId && persona.provincia !== provinciaId) return false;

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
      this.personaSeleccionada = null;
      this.asignacion.persona = 0;
      this.personasFiltradas = this.getPersonasActivas();
      return;
    }
    this.asignacion.instalacion = this.instalacionSeleccionada;
    this.asignacion.puesto = 0;
    this.puestos = [];
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
        if (preselectPuestoId) {
          this.asignacion.puesto = preselectPuestoId;
        }
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
      && !!this.asignacion.patronAsignacion
      && !!this.asignacion.start_date;
    }

  onSave(): void {
    if (!this.isFormValid()) return;
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
