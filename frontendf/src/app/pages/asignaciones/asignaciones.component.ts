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
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatCardModule } from '@angular/material/card';


@Component({
  selector: 'app-asignaciones',
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
      rotativo: false,
      estado: 'ACTIVO'
    };
  }

  onClientChange(): void{
    console.log('🏢 Cliente seleccionado:', this.clienteSeleccionado);
    this.instalacionSeleccionada = null;
    this.asignacionActual.instalacion = 0;
    this.asignacionActual.puesto = 0;
    this.instalaciones = [];
    this.puestos = [];
    
    if(this.clienteSeleccionado){
      this.instalacionService.getInstalaciones().subscribe({
        next: (data) => {
          console.log('📦 Todas las instalaciones:', data);
          this.instalaciones = data.filter(ins => ins.cliente_id === this.clienteSeleccionado);
          console.log('✅ Instalaciones filtradas:', this.instalaciones);
        },
        error: (err) => console.error('❌ Error al cargar instalaciones', err)
      });
    }
  }

  onInstalacionChange(): void{
    console.log('🏭 Instalación seleccionada:', this.instalacionSeleccionada);
    this.asignacionActual.puesto = 0;
    this.puestos = []

    if (this.instalacionSeleccionada){
      this.puestoService.getPuestosPorInstalacion(this.instalacionSeleccionada).subscribe({
        next: (data) => {
          this.puestos = data;
          console.log('✅ Puestos cargados:', this.puestos);
        },
        error: (err) => console.error('❌ Error al cargar puestos', err) 
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
    this.mostrarModal = true;
  }

  abrirModalEditar(asignacion: Asignacion): void{
    this.modoEdicion = true;
    this.textoBotonAsignacion = 'Actualizar';
    this.asignacionActual = {...asignacion}
    this.clienteSeleccionado = asignacion.cliente;
    this.instalacionSeleccionada = asignacion. instalacion;

    this.instalacionService.getInstalaciones().subscribe({
      next: (data) =>{
       this.instalaciones = data.filter(ins => ins.cliente_id === this.clienteSeleccionado);
        if (this.instalacionSeleccionada){
          this.puestoService.getPuestosPorInstalacion(this.instalacionSeleccionada).subscribe({
            next: (puestos) => this.puestos = puestos,
            error: (err) => console.error('Error al cargar puestos', err)
          });
        }
      },
      error: (err) => console.error('Error al cargar instaaciones', err)
    });
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
      // Mostrar la lista de asignaciones actuales para depuración
      console.log('📋 Asignaciones actuales:', this.asignaciones);
    // Validar campos obligatorios
    if (!this.clienteSeleccionado) {
      alert('Debe seleccionar un Cliente');
      return;
    }
    if (!this.instalacionSeleccionada) {
      alert('Debe seleccionar una Instalación');
      return;
    }
    if (!this.asignacionActual.puesto || this.asignacionActual.puesto === 0) {
      alert('Debe seleccionar un Puesto');
      return;
    }
    if (!this.asignacionActual.persona || this.asignacionActual.persona === 0) {
      alert('Debe seleccionar una Persona');
      return;
    }
    if (!this.asignacionActual.horario || this.asignacionActual.horario === 0) {
      alert('Debe seleccionar un Horario');
      return;
    }
    this.asignacionActual.cliente = this.clienteSeleccionado!;
    this.asignacionActual.instalacion = this.instalacionSeleccionada!;
    this.asignacionActual.mes = this.mes;
    this.asignacionActual.anio = this.anio;

    // Validación para evitar duplicados en el frontend
    const yaExiste = this.asignaciones.some(asig =>
      asig.persona === this.asignacionActual.persona &&
      asig.mes === this.asignacionActual.mes &&
      asig.anio === this.asignacionActual.anio &&
      (!this.modoEdicion || (this.modoEdicion && asig.id !== this.asignacionActual.id))
    );
    if (yaExiste) {
      alert('Ya existe una asignación para esta persona en el mes y año seleccionados. Edite la existente o elimínela antes de crear una nueva.');
      return;
    }

    console.log('💾 Datos a enviar:', this.asignacionActual);

    if (this.modoEdicion && this.asignacionActual.id){
      this.asignacionService.actualizarAsignacion(this.asignacionActual.id, this.asignacionActual).subscribe({
        next: () => {
          alert('Asignación actualizada con éxito');
          this.cargarAsignaciones();
          this.cerrarModal();
        },
        error: (err) =>{
          console.error('❌ Error completo:', err);
          console.error('❌ Detalles del error:', err.error);
          alert('Error al actualizar la asignación: ' + JSON.stringify(err.error))
        } 
      });
    } else {
      this.asignacionService.crearAsignacion(this.asignacionActual).subscribe({
        next: () =>{
          alert('Asignacion Creada correctamente');
          this.cargarAsignaciones();
          this.cerrarModal();
        },
        error: (err) =>{
          console.error('❌ Error completo:', err);
          console.error('❌ Detalles del error:', err.error);
          alert('Error al crear: ' + JSON.stringify(err.error));
        }
      });
    }
  }

  eliminarAsignacion(asignacion: Asignacion): void {
    if (confirm(`¿Estás seguro de eliminar la asignación de ${asignacion.persona}?`)){
      this.asignacionService.eliminarAsignacion(asignacion.id!).subscribe({
        next: () => {
          alert('Asignacion eliminada con exito');
          this.cargarAsignaciones();
        },
        error: (err) =>{
          console.error(`Error al eliminar asignacion de ${asignacion.persona}`, err);
          alert('Error al eliminar la asignacion');
        }
      });
    }
  }

  cambiarMesAnio(): void{
    this.cargarAsignaciones();
  }
 

}
