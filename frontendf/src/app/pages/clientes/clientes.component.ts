import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { ClienteService } from '../../services/cliente.service';
import { Cliente } from '../../models';

@Component({
  selector: 'app-clientes',
  imports: [CommonModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule],
  templateUrl: './clientes.component.html',
  styleUrl: './clientes.component.css'
})
export class ClientesComponent implements OnInit {
  clientes: Cliente[] = [];
  disployedColumns: string[] = ['id', 'razon_social', 'nombre_comercial', 'actions'];

  constructor(private clienteService: ClienteService) {}

  ngOnInit(): void {
      this.loadClientes();
    }

   loadClientes(): void {
    this.clienteService.getClientes().subscribe({
      next: data => this.clientes = data,
      error: err => console.error('Error al cargar clientes:', err)
    });
  }  


  deleteCliente(id?: number): void {
    if (!id) return;
    if (confirm('¿Estás seguro de que deseas eliminar este cliente?')) {
      this.clienteService.deleteCliente(id).subscribe({
        next: () => this.loadClientes(),
        error: err => console.error('Error al eliminar cliente:', err)
      });
    }
  }
  
}
