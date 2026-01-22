import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { Cliente } from '../../models';
import { InstalacionService } from '../../services/instalacion.service';
import { ClienteService } from '../../services/cliente.service';
import { InstalacionFormComponent } from './instalacion-form/instalacion-form.component';

@Component({
  selector: 'app-instalaciones',
  standalone: true,
  imports: [CommonModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule, MatDialogModule],
  templateUrl: './instalaciones.component.html',
  styleUrl: './instalaciones.component.css'
})
export class InstalacionesComponent implements OnInit{
  instalaciones: any[] = [];
  clientes: Cliente[] = [];
  showDeleteModal: boolean = false;
  instalacionAEliminar: any = null;

  constructor(
    private instalacionService: InstalacionService,
    private clienteService: ClienteService,
    private dialog: MatDialog
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

  abrirModal(instalacion?: any): void {
    const dialogRef = this.dialog.open(InstalacionFormComponent, {
      width: '500px',
      data: { instalacion: instalacion || null, clientes: this.clientes }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (instalacion?.id) {
          this.actualizarInstalacion(instalacion.id, result);
        } else {
          this.crearInstalacion(result);
        }
      }
    });
  }

  crearInstalacion(data: any): void {
    this.instalacionService.createInstalacion(data).subscribe({
      next: () => {
        alert('Instalación creada exitosamente');
        this.cargarInstalaciones();
      },
      error: (error: any) => {
        console.error('Error al crear instalación:', error);
        alert('Error al crear instalación');
      }
    });
  }

  actualizarInstalacion(id: number, data: any): void {
    const payload = {
      nombre: data.nombre_instalacion,
      cliente: data.cliente_id,
      provincia: data.provincia,
      ciudad: data.ciudad
    };

    this.instalacionService.updateInstalacion(id, payload).subscribe({
      next: () => {
        alert('Instalación actualizada exitosamente');
        this.cargarInstalaciones();
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
