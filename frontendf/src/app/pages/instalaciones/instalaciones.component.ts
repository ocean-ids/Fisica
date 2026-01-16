import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Cliente } from '../../models';
import { InstalacionService } from '../../services/instalacion.service';
import { ClienteService } from '../../services/cliente.service';

@Component({
  selector: 'app-instalaciones',
  imports: [CommonModule, FormsModule],
  templateUrl: './instalaciones.component.html',
  styleUrl: './instalaciones.component.css'
})
export class InstalacionesComponent implements OnInit{
  instalaciones: any[] = [];
  clientes: Cliente[] = [];

  showModal: boolean = false;
  showDeleteModal: boolean = false;
  isEditMode: boolean = false;

  nuevaInstalacion: any = {
    nombre_instalacion: '',
    cliente_id: '',
    provincia: '',
    ciudad: ''
  };

  instalacionSeleccionada: any = null;
  instalacionAEliminar: any = null;

  constructor(
    private instalacionService: InstalacionService,
    private clienteService: ClienteService
  ){}

  ngOnInit(): void{
    this.cargarInstalaciones();
    this.cargarClientes();
  }

  cargarInstalaciones(): void{
    this.instalacionService.getInstalaciones().subscribe({
      next: (data) =>{
        this.instalaciones = data;
        console.log('instalaciones cargadas', this.instalaciones);
      },
      error: (error) => console.error('Error al cargar instalaciones: ')
    });
  }

  cargarClientes(): void{
  this.clienteService.getClientes().subscribe({
    next: (data) => {
      this.clientes = data;
      console.log('Clientes cargados', this.clientes);   
    },
    error: (error: any) => console.error('Error al cargar clientes:', error)
  });
}

  abrirModal(): void{
    this.isEditMode = false;
    this.resetFormulario();
    this.showModal = true;
  }

  abrirModalEditar(instalacion: any): void{
    this.isEditMode = true;
    this.instalacionSeleccionada = {...instalacion};
    this.showModal = true
  }

  cerrarModal(): void{
    this.showModal = false;
    this.resetFormulario();
  }

  resetFormulario(): void {
    this.nuevaInstalacion = {
      nombre_instalacion: '',
      cliente_id: '',
      provincia: '',
      ciudad: ''
    };
    this.instalacionSeleccionada = null;
  }

  guardarInstalacion(): void{
    if(this.isEditMode){
      this.actualizarInstalacion();
    }else{
      this.crearInstalacion();
    }
  }

  crearInstalacion(): void {
    console.log('Datos a enviar:', this.nuevaInstalacion);
    
    this.instalacionService.createInstalacion(this.nuevaInstalacion).subscribe({
      next: (response: any) => {
        console.log('Instalación creada:', response);
        alert('Instalación creada exitosamente');
        this.cargarInstalaciones();
        this.cerrarModal();
      },
      error: (error: any) => {
        console.error('Error al crear instalación:', error);
        alert('Error al crear instalación');
      }
    });
  }

  actualizarInstalacion(): void {
    const payload = {
      nombre: this.instalacionSeleccionada.nombre,
      cliente: this.instalacionSeleccionada.cliente_id,
      provincia: this.instalacionSeleccionada.provincia,
      ciudad: this.instalacionSeleccionada.ciudad
    };

    console.log('Datos a actualizar:', payload);

    this.instalacionService.updateInstalacion(this.instalacionSeleccionada.id, payload).subscribe({
      next: (response: any) => {
        console.log('Instalación actualizada:', response);
        alert('Instalación actualizada exitosamente');
        this.cargarInstalaciones();
        this.cerrarModal();
      },
      error: (error: any) => {
        console.error('Error al actualizar instalación:', error);
        alert('Error al actualizar instalación');
      }
    });
  }

  confirmarEliminar(instalacion: any): void{
    this.instalacionAEliminar = instalacion;
    this.showDeleteModal = true;
  }

  cerrarModalEliminar(): void{
    this.showDeleteModal = false;
    this.instalacionAEliminar = null;
  }

  eliminarInstalacion(): void {
    if (this.instalacionAEliminar) {
      this.instalacionService.deleteInstalacion(this.instalacionAEliminar.id).subscribe({
        next: (response: any) => {
          console.log('Instalación eliminada:', response);
          alert('Instalación eliminada exitosamente');
          this.cargarInstalaciones();
          this.cerrarModalEliminar();
        },
        error: (error: any) => {
          console.error('Error al eliminar instalación:', error);
          alert('Error al eliminar instalación');
        }
      });
    }
  }

  getNombreCliente(clienteId: number): string {
    const cliente = this.clientes.find(c => c.id === clienteId);
    return cliente ? cliente.nombre_comercial : 'N/A';
  }

}
