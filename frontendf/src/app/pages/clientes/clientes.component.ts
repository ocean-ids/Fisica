import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { ClienteService } from '../../services/cliente.service';
import { Cliente } from '../../models/cliente.model';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ClienteFormComponent } from './cliente-form/cliente-form.component';

@Component({
  selector: 'app-clientes',
  standalone: true,
  imports: [CommonModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule, MatDialogModule],
  templateUrl: './clientes.component.html',
  styleUrl: './clientes.component.css'
})
export class ClientesComponent implements OnInit {
  clientes: Cliente[] = [];
  displayedColumns = ['razon_social', 'nombre_comercial', 'direccion', 'acciones'];

  constructor(
    private clienteService: ClienteService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.loadClientes();
  }

  loadClientes(): void {
    this.clienteService.getClientes().subscribe({
      next: data => this.clientes = data,
      error: err => console.error('Error al cargar clientes:', err)
    });
  }
  openDialog(cliente?: Cliente): void {
    const dialogRef = this.dialog.open(ClienteFormComponent, {
      width: '500px',
      data: cliente || {}
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (cliente?.id) {
          this.updateCliente(cliente.id, result);
        } else {
          this.createCliente(result);
        }
      }
    });
  }

  createCliente(cliente: Cliente): void {
    this.clienteService.createCliente(cliente).subscribe({
      next: () => this.loadClientes(),
      error: (err: any) => console.error('Error:', err)
    });
  }

  updateCliente(id: number, cliente: Cliente): void {
    this.clienteService.updateCliente(id, cliente).subscribe({
      next: () => this.loadClientes(),
      error: (err: any) => console.error('Error:', err)
    });
  }

  deleteCliente(id?: number): void {
    if (!id) return;
    if (confirm('¿Eliminar este cliente?')) {
      this.clienteService.deleteCliente(id).subscribe({
        next: () => this.loadClientes(),
        error: err => console.error('Error al eliminar:', err)
      });
    }
  }
}