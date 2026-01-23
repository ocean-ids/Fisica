import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {Cliente, Persona, Instalacion, Puesto, Horario, Asignacion} from '../../models';
import { ClienteService } from '../../services/cliente.service';
import { InstalacionService } from '../../services/instalacion.service';
import { PuestoService } from '../../services/puesto.service';
import { PersonaService } from '../../services/persona.service';
import { HorarioService } from '../../services/horario.service';
import { AsignacionService, } from '../../services/asignacion.service';


@Component({
  selector: 'app-asignaciones',
  imports: [CommonModule, FormsModule],
  templateUrl: './asignaciones.component.html',
  styleUrl: './asignaciones.component.css'
})
export class AsignacionesComponent implements OnInit {

  
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
  ){}


  ngOnInit(): void {
    this.cargarCatalogos();
    this.cargarAsignaciones();
  }

  cargarCatalogos(): void {
    this.clienteService.getClientes().subscribe({
      next: (data) => this.clientes = data,
      error: (err) => console.error('Error al cargar clientes', err)
      
    });

    this.personaService.getPersonas().subscribe({
      next: (data) => this.personas = data,
      error: (err) => console.error('Error al cargar personas', err)
    });

    this.horarioService.obtenerHorarios().subscribe({
      next: (data) => this.horarios = data,
      error: (err) => console.error('Error al cargar horarios', err)
    });
  }


  cargarAsignaciones(): void{
    this.asignacionService.obtenerAsignaciones(this.mes, this.anio).subscribe({
      next: (data) => this.asignaciones = data,
      error: (err) => console.error('Error al cargar asignaciones', err)
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
      fecha_inicio: '',
      fecha_fin: '',
      rotativo: false,
      orden: 0,
      estado: 'ACTIVO'
    };
  }

  onClientChange(): void{
    this.instalacionSeleccionada = null;
    this.asignacionActual.instalacion = 0;
    this.asignacionActual.puesto = 0;
    this.instalaciones = [];
    this.puestos = [];
    
    if(this.clienteSeleccionado){
      this.instalacionService.getInstalaciones().subscribe({
        next: (data) => {
          this.instalaciones = data.filter(ins => ins.cliente === this.clienteSeleccionado)
        },
        error: (err) => console.error('Error al cargar instalaciones', err)
      });
    }
  }

  onInstalacionChange(): void{
    this.asignacionActual.puesto = 0;
    this.puestos = []

    if (this.instalacionSeleccionada){
      this.puestoService.getPuestosPorInstalacion(this.instalacionSeleccionada).subscribe({
        next: (data) => this.puestos = data,
        error: (err) => console.error('Error al cargar puestos', err) 
      });
    }
  }

  abrirModalNuevo(): void {
    this.modoEdicion = false;
    this.asignacionActual = this.nuevaAsignacion();
    this.clienteSeleccionado = null;
    this.instalacionSeleccionada = null;
    this.instalaciones = [];
    this.puestos = [];
    this.mostrarModal = true;
  }

  abrirModalEditar(asignacion: Asignacion): void {
    this.modoEdicion = true;
    this.asignacionActual = { ...asignacion };
    this.clienteSeleccionado = asignacion.cliente;
    this.instalacionSeleccionada = asignacion.instalacion;
    
    
    this.instalacionService.getInstalaciones().subscribe({
      next: (data) => {
        this.instalaciones = data.filter(ins => ins.cliente === this.clienteSeleccionado);
        
       
        if (this.instalacionSeleccionada) {
          this.puestoService.getPuestosPorInstalacion(this.instalacionSeleccionada).subscribe({
            next: (puestos) => this.puestos = puestos,
            error: (err) => console.error('Error al cargar puestos', err)
          });
        }
      },
      error: (err) => console.error('Error al cargar instalaciones', err)
    });
    
    this.mostrarModal = true;
  }

  cerrarModal(): void {
    this.mostrarModal = false
    this.asignacionActual = this.nuevaAsignacion();
    this.clienteSeleccionado = null;
    this.instalacionSeleccionada = null;
    this.instalaciones = [];
    this.puestos = [];
  }

  guardarAsignacion(): void {

    this.asignacionActual.cliente = this.clienteSeleccionado!;
    this.asignacionActual.instalacion = this.instalacionSeleccionada!;
    this.asignacionActual.mes = this.mes;
    this.asignacionActual.anio = this.anio;

    if (this.modoEdicion && this.asignacionActual.id) {
     
      this.asignacionService.actualizarAsignacion(this.asignacionActual.id, this.asignacionActual).subscribe({
        next: () => {
          alert('Asignación actualizada correctamente');
          this.cargarAsignaciones();
          this.cerrarModal();
        },
        error: (err) => {
          console.error('Error al actualizar', err);
          alert('Error al actualizar la asignación');
        }
      });
    } else {
      this.asignacionService.crearAsignacion(this.asignacionActual).subscribe({
        next: () => {
          alert('Asignación creada correctamente');
          this.cargarAsignaciones();
          this.cerrarModal();
        },
        error: (err) =>{
          console.error('Error al crear', err);
          alert('Error al crear la asignación');
        }
      });
    }
  }

  eliminarAsignación(id: number): void{
    if(confirm('¿Estas seguro de eliminar esta asignación?')){
      this.asignacionService.eliminarAsignacion(id).subscribe({
        next: () => {
          alert('Asignación eliminada correctamente'),
          this.cargarAsignaciones();
        },
        error: (err) =>{
          console.error('Error al eliminar');
          alert('Error al eliminar la asignación')
        }
      });
    }
  }

  cargarMesAnio(): void{
    this.cargarAsignaciones()
  }
 

}
