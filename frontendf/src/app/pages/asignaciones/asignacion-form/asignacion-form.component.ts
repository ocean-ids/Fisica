import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
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
    MatInputModule
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
    if (this.clienteSeleccionado) {
      this.cargarInstalaciones(this.clienteSeleccionado, this.instalacionSeleccionada || undefined, this.asignacion.puesto || undefined);
    }
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
    this.cargarInstalaciones(this.clienteSeleccionado);
  }

  onInstalacionChange(): void {
    if (!this.instalacionSeleccionada) {
      this.asignacion.instalacion = 0;
      this.asignacion.puesto = 0;
      this.puestos = [];
      return;
    }
    this.asignacion.instalacion = this.instalacionSeleccionada;
    this.asignacion.puesto = 0;
    this.puestos = [];
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

  onSave(): void {
    this.dialogRef.close({
      action: 'save',
      asignacion: this.asignacion,
      clienteSeleccionado: this.clienteSeleccionado,
      instalacionSeleccionada: this.instalacionSeleccionada
    });
  }
}
