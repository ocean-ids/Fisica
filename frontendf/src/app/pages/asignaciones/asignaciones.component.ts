import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Cliente, Persona, Instalacion, Puesto, Horario, Asignacion } from '../../models';
import { ClienteService } from '../../services/cliente.service';
import { InstalacionService } from '../../services/instalacion.service';
import { PuestoService } from '../../services/puesto.service';
import { PersonaService } from '../../services/persona.service';
import { HorarioService } from '../../services/horario.service';
import { AsignacionService } from '../../services/asignacion.service';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatCardModule } from '@angular/material/card';
import { HttpClient } from '@angular/common/http';
import { saveAs } from 'file-saver';

@Component({
  selector: 'app-asignaciones',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatCardModule
  ],
  templateUrl: './asignaciones.component.html',
  styleUrl: './asignaciones.component.css'
})
export class AsignacionesComponent implements OnInit {

  textoBotonAsignacion: string = 'Guardar';

  asignaciones: Asignacion[] = [];

  mes: number = new Date().getMonth() + 1;
  anio: number = new Date().getFullYear();

  clientes: Cliente[] = [];
  personas: Persona[] = [];
  horarios: Horario[] = [];
  instalaciones: Instalacion[] = [];
  puestos: Puesto[] = [];

  clienteSeleccionado: number | null = null;
  instalacionSeleccionada: number | null = null;

  mostrarModal: boolean = false;
  asignacionActual: Asignacion = this.nuevaAsignacion();
  modoEdicion: boolean = false;

  constructor(
    private clienteService: ClienteService,
    private instalacionService: InstalacionService,
    private puestoService: PuestoService,
    private personaService: PersonaService,
    private horarioService: HorarioService,
    private asignacionService: AsignacionService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.cargarCatalogos();
    this.cargarAsignaciones();
  }

  cargarCatalogos(): void {
    this.clienteService.getClientes().subscribe({
      next: data => this.clientes = data,
      error: err => console.error('Error al cargar clientes', err)
    });

    this.personaService.getPersonas().subscribe({
      next: data => this.personas = data,
      error: err => console.error('Error al cargar personas', err)
    });

    this.horarioService.obtenerHorarios().subscribe({
      next: data => this.horarios = data,
      error: err => console.error('Error al cargar horarios', err)
    });
  }

  cargarAsignaciones(): void {
    this.asignacionService.obtenerAsignaciones(this.mes, this.anio).subscribe({
      next: data => this.asignaciones = data,
      error: err => console.error('Error al cargar asignaciones', err)
    });
  }

  nuevaAsignacion(): Asignacion {
    return {
      persona: 0,
      cliente: 0,
      instalacion: 0,
      puesto: 0,
      horario: 0,
      mes: this.mes,
      anio: this.anio,
      rotativo: false,
      estado: 'ACTIVO',
      clienteCodigo: ''
    };
  }

  
  onClientChange(): void {
    this.asignacionActual.cliente = this.clienteSeleccionado!;
    this.instalacionSeleccionada = null;
    this.asignacionActual.instalacion = 0;
    this.asignacionActual.puesto = 0;
    this.instalaciones = [];
    this.puestos = [];

    if (this.clienteSeleccionado) {
      this.instalacionService.getInstalaciones().subscribe({
        next: data => {
          this.instalaciones = data.filter(
            i => i.cliente_id === this.clienteSeleccionado
          );
        },
        error: err => console.error('Error al cargar instalaciones', err)
      });
    }
  }

  onInstalacionChange(): void {
    this.asignacionActual.instalacion = this.instalacionSeleccionada!;
    this.asignacionActual.puesto = 0;
    this.puestos = [];

    if (this.instalacionSeleccionada) {
      this.puestoService.getPuestosPorInstalacion(this.instalacionSeleccionada)
        .subscribe({
          next: data => this.puestos = data,
          error: err => console.error('Error al cargar puestos', err)
        });
    }
  }


  abrirModalNuevo(): void {
    this.modoEdicion = false;
    this.textoBotonAsignacion = 'Guardar';
    this.asignacionActual = this.nuevaAsignacion();
    this.clienteSeleccionado = null;
    this.instalacionSeleccionada = null;
    this.instalaciones = [];
    this.puestos = [];
    if (this.clientes.length === 0 || this.personas.length === 0 || this.horarios.length === 0) {
      this.cargarCatalogos();
    }
   
    if (this.instalacionSeleccionada) {
      this.onInstalacionChange();
    }
    this.mostrarModal = true;
  }

  descargarReporteExcel() {
  this.http.get('http://localhost:8000/api/reporte-asignaciones/', { responseType: 'blob' })
    .subscribe(blob => {
      saveAs(blob, 'reporte_asignaciones.xlsx');
    });
  }

  abrirModalEditar(asignacion: Asignacion): void {
    this.modoEdicion = true;
    this.textoBotonAsignacion = 'Actualizar';
    this.asignacionActual = { ...asignacion };

    this.clienteSeleccionado = asignacion.cliente;
    this.instalacionSeleccionada = asignacion.instalacion;

    this.onClientChange();
    this.onInstalacionChange();

    this.mostrarModal = true;
  }

  cerrarModal(): void {
    this.mostrarModal = false;
    this.asignacionActual = this.nuevaAsignacion();
    this.clienteSeleccionado = null;
    this.instalacionSeleccionada = null;
    this.instalaciones = [];
    this.puestos = [];
  }

  guardarAsignacion(): void {

    if (!this.clienteSeleccionado) {
      alert('Debe seleccionar un Cliente');
      return;
    }
    if (!this.instalacionSeleccionada) {
      alert('Debe seleccionar una Instalación');
      return;
    }
    if (!this.asignacionActual.puesto) {
      alert('Debe seleccionar un Puesto');
      return;
    }
    if (!this.asignacionActual.persona) {
      alert('Debe seleccionar una Persona');
      return;
    }
    if (!this.asignacionActual.horario) {
      alert('Debe seleccionar un Horario');
      return;
    }

    this.asignacionActual.cliente = this.clienteSeleccionado;
    this.asignacionActual.instalacion = this.instalacionSeleccionada;
    this.asignacionActual.mes = this.mes;
    this.asignacionActual.anio = this.anio;

    const yaExiste = this.asignaciones.some(a =>
      a.persona === this.asignacionActual.persona &&
      a.mes === this.mes &&
      a.anio === this.anio &&
      (!this.modoEdicion || a.id !== this.asignacionActual.id)
    );

    if (yaExiste) {
      alert('Ya existe una asignación para esta persona en este mes.');
      return;
    }

    if (this.modoEdicion && this.asignacionActual.id) {
      this.asignacionService.actualizarAsignacion(
        this.asignacionActual.id,
        this.asignacionActual
      ).subscribe({
        next: () => {
          alert('Asignación actualizada');
          this.cargarAsignaciones();
          this.cerrarModal();
        },
        error: err => {
          console.error(err);
          alert('Error al actualizar');
        }
      });
    } else {
      this.asignacionService.crearAsignacion(this.asignacionActual).subscribe({
        next: () => {
          alert('Asignación creada');
          this.cargarAsignaciones();
          this.cerrarModal();
        },
        error: err => {
          console.error(err);
          alert('Error al crear');
        }
      });
    }
  }

  eliminarAsignacion(asignacion: Asignacion): void {
    if (confirm(`¿Eliminar la asignación de ${asignacion.persona_detalle?.apellidos} ${asignacion.persona_detalle?.nombres}?`)) {
      this.asignacionService.eliminarAsignacion(asignacion.id!).subscribe({
        next: () => {
          alert('Asignación eliminada');
          this.cargarAsignaciones();
        },
        error: err => {
          console.error(err);
          alert('Error al eliminar');
        }
      });
    }
  }

  cambiarMesAnio(): void {
    this.cargarAsignaciones();
  }
}
