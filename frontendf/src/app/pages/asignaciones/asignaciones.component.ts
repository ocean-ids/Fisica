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
      error: (err) => console.error(" Error al cargar clientes", err)
      
    });

    this.personaService.getPersonas().subscribe({
      next: (data) => this.personas = data,
      error: (err) => console.error("Error al cargar personas", err)
    });

    this.horarioService.obtenerHorarios().subscribe({
      next: (data) => this.horarios = data,
      error: (err) => console.error("Error al cargar horarios", err)
    });
  }


  cargarAsignaciones(): void{
    this.asignacionService.obtenerAsignaciones(this.mes, this.anio).subscribe({
      next: (data) => this.asignaciones = data,
      error: (err) => console.error("Error al cargar asignaciones", err)
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

  

 

}
