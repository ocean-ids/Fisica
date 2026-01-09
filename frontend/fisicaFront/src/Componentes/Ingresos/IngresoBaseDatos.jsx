// IMPORTS
import React, { useState, useEffect } from 'react';
import './Ingreso.css';
import { MaterialReactTable } from "material-react-table";
import { Box, Button } from "@mui/material";
import Swal from 'sweetalert2';
import DeleteIcon from '@mui/icons-material/Delete';

const provincias = ['ESMERALDAS', 'GUAYAS', 'MANABÍ', 'SANTA ELENA', 'LOS RÍOS', 'EL ORO', 'CARCHI', 'IMBABURA', 'PICHINCHA', 'COTOPAXI', 'TUNGURAHUA', 'CHIMBORAZO', 'BOLÍVAR', 'CAÑAR', 'AZUAY', 'SUCUMBÍOS', 'NAPO', 'ORELLANA', 'PASTAZA', 'MORONA CHINCHIPE', 'GALÁPAGOS'];
const ciudades = ['QUITO', 'GUAYAQUIL', 'MANTA','RIOBAMBA','AMBATO','LATACUNGA','CUENCA', 'SANTO DOMINGO', 'DURÁN', 'MACHALA', 'PORTOVIEJO', 'ESMERALDAS', 'LOJA','IBARRA'];
const tipo = ['FIJO', 'SACAFRANCO', 'SUPERVISOR'];

/*const horas = Array.from({ length: 24 }, (_, i) => (i + 1).toString());*/
const horas = [];
for (let i = 1; i <= 24; i += 0.5) {
  horas.push(i % 1 === 0 ? i.toString() : i.toFixed(1));
}

const dias = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
const turnos = ['D', 'N'];

const Formulario = () => {
  const [form, setForm] = useState({
    razon_social: '',
    nombre_comercial: '',
    direccion: '',
    nombre_instalacion: '',
    ciudad: '',
    provincia: '',
    codigo: '',
    nombre_puesto: '',
    nombre: '',
    apellido: '',
    cedula: '',
    hora_ingreso: '',
    hora_salida: '',
    tipo: ''
  });




   const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

    const [clientes, setClientes] = useState([]); // Lista de razones sociales
  const [tablaHorario, setTablaHorario] = useState([{ horas: '', turno:'',dias: [] }]);
    const [instalaciones, setInstalaciones] = useState([]);


  const handleHoraChange = (index, value) => {
    const newTabla = [...tablaHorario];
    newTabla[index].horas = value;
    setTablaHorario(newTabla);
  };

  const handleCheckboxChange = (index, dia, checked) => {
    const newTabla = [...tablaHorario];
    const diasSeleccionados = newTabla[index].dias;
    newTabla[index].dias = checked
      ? [...diasSeleccionados, dia]
      : diasSeleccionados.filter(d => d !== dia);
    setTablaHorario(newTabla);
  };

    const handleCheckboxChangeTurno = (index, turno, checked) => {
    const newTabla = [...tablaHorario];
    const turnoSeleccionado = newTabla[index].turno;
    newTabla[index].turno = checked
      ? [...turnoSeleccionado, turno]
      : turnoSeleccionado.filter(d => d !== turno);
    setTablaHorario(newTabla);
  };

  const handleEliminarFila = (index) => {
    const nuevasFilas = [...tablaHorario];
    nuevasFilas.splice(index, 1);
    setTablaHorario(nuevasFilas);
  };

  const columns = [
    {
      accessorKey: 'horas',
      header: 'Horas',
      Cell: ({ row }) => {
        const index = row.index;
        return (
          <select
            value={tablaHorario[index].horas}
            onChange={(e) => handleHoraChange(index, e.target.value)}
            style={{ width: '70px', fontSize: '12px' }}
          >
            <option value="">Seleccione</option>
            {horas.map(h => <option key={h}>{h}</option>)}
          </select>
        );
      },
    },
        {
      accessorKey: 'turno',
      header: 'Turno',
      Cell: ({ row }) => {
        const index = row.index;
        console.log(tablaHorario)
        return (
          <div style={{ display: 'flex', gap: '4px', fontSize: '12px' }}>
            {turnos.map((turno) => (
              <label key={turno} style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                <input
                  type="checkbox"
                  checked={tablaHorario[index].turno.includes(turno)}
                  onChange={(e) => handleCheckboxChangeTurno(index, turno, e.target.checked)}
                  disabled={tablaHorario[index].horas == "24"}
                />
                {turno}
              </label>
            ))}
          </div>
        );
      },
    },
    {
      accessorKey: 'dias',
      header: 'Días',
      Cell: ({ row }) => {
        const index = row.index;
        return (
          <div style={{ display: 'flex', gap: '4px', fontSize: '12px' }}>
            {dias.map((dia) => (
              <label key={dia} style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                <input
                  type="checkbox"
                  checked={tablaHorario[index].dias.includes(dia)}
                  onChange={(e) => handleCheckboxChange(index, dia, e.target.checked)}
                />
                {dia}
                
              </label>
            ))}
          </div>
        );
      },
    },

    {
      accessorKey: 'acciones',
      header: 'Acción',
      Cell: ({ row }) => (
        <Button
          variant="outlined"
          color="error"
          onClick={() => handleEliminarFila(row.index)}
        >
          <DeleteIcon />
        </Button>
      ),
    },
  ];

  // Fetch Clientes


  const crearCliente = async () => {
  await fetch('http://localhost:8000/api/crear-cliente/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      razon_social: form.razon_social,
      nombre_comercial: form.nombre_comercial,
      direccion: form.direccion
    })
  })
  .then(res => res.json())
  .then(data => {
    Swal.fire({
      icon: 'success',
      title: '¡Listo!',
      text: data.message,
    });

    fetchClientes();
  })
  .catch(err => {
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: 'Ocurrió un problema al crear Cliente.',
    });
  });
};

const convertirDenominativo = (tablaHorario) => {
  
  return tablaHorario.map(item => {
    console.log(item.dias[0]+item.dias[item.dias.length-1])
    return `${item.horas}H${item.turno}${item.dias.join('')}`;
  }).join(' ');
};

  const crearHorario = async () => {
    const denominativoString = convertirDenominativo(tablaHorario);
    console.log(denominativoString)
    await fetch('http://localhost:8000/api/crear-horario/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      hora_ingreso: form.hora_ingreso,
      hora_salida: form.hora_salida,
      denominativo: denominativoString,
          })
})
.then(res => res.json())

.then(data => {
  Swal.fire({
    icon: 'success',
    title: '¡Listo!',
    text: data.message,
  });
})
.catch(err => {
  Swal.fire({
    icon: 'error',
    title: 'Error',
    text: 'Ocurrió un problema al crear el horario.',
    });
    });
  };

  const crearPersona = async () => {
    await fetch('http://localhost:8000/api/crear-persona/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      nombres: form.nombre,
      apellidos: form.apellido,
      cedula: form.cedula,
      tipo: form.tipo
          })
})
.then(res => res.json())
.then(data => {
  Swal.fire({
    icon: 'success',
    title: '¡Listo!',
    text: data.message,
  });
})
.catch(err => {
  Swal.fire({
    icon: 'error',
    title: 'Error',
    text: 'Ocurrió un problema al crear Persona.',
    });
    });
  };




  const crearPuesto = async () => {
  await fetch('http://localhost:8000/api/crear-puesto/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
      nombre: form.nombre_puesto,
      instalacion_id: form.id_instalacion
    })
})
.then(res => res.json())
.then(data => {
  Swal.fire({
    icon: 'success',
    title: '¡Listo!',
    text: data.message,
  });
})
.catch(err => {
  Swal.fire({
    icon: 'error',
    title: 'Error',
    text: 'Ocurrió un problema al crear el puesto.',
  });
});
};







    const fetchClientes = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/clientes/');
        const data = await res.json();
        setClientes(data);
      } catch (error) {
        console.error('Error al cargar clientes:', error);
      }
    };

    const crearInstalacion = async () => {
  try {
    const res = await fetch('http://localhost:8000/api/crear-instalacion/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        nombre_instalacion: form.nombre_instalacion,
        cliente_id: form.razon_social_instalacion,
        codigo: form.codigo,
        ciudad: form.ciudad,
        provincia: form.provincia
      })
    });

    const data = await res.json();

    Swal.fire({
      icon: 'success',
      title: '¡Listo!',
      text: data.message,
    });

    // Aquí refrescamos las instalaciones para que el combo tenga la nueva instalación
    await fetchInstalaciones();

  } catch (err) {
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: 'Ocurrió un problema al crear instalación.',
    });
  }
};
  

  useEffect(() => {
  
    fetchClientes();
  }, []);

      const fetchInstalaciones = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/instalaciones/');
        const data = await res.json();
        setInstalaciones(data);
      } catch (error) {
        console.error('Error al cargar instalaciones:', error);
      }
    };

useEffect(() => {

    fetchInstalaciones();
  }, []); 

  return (
    <div className="form-wrapper">
      <form className="grid-form">

        {/* PERSONA */}
        <div className="form-column">
          <h3>PERSONA</h3>
          <label>NOMBRES:
            <input name="nombre" value={form.nombre} onChange={handleChange} />
          </label>
          <label>APELLIDOS:
            <input name="apellido" value={form.apellido} onChange={handleChange} />
          </label>
          <label>CÉDULA:
            <input name="cedula" value={form.cedula} onChange={handleChange} />
          </label>
          <label>TIPO:
            <select name="tipo" value={form.tipo} onChange={handleChange}>
              <option value="">-- Seleccione --</option>
              {tipo.map(p => <option key={p}>{p}</option>)}
            </select>
          </label>
          <button type="button" className="btn" onClick={crearPersona}>Crear Persona</button>
        </div>

        {/* CLIENTE */}
        <div className="form-column">
          <h3>CLIENTE</h3>
          <label>RAZÓN SOCIAL:
            <input name="razon_social" value={form.razon_social} onChange={handleChange} />
          </label>
          <label>NOMBRE COMERCIAL:
            <input name="nombre_comercial" value={form.nombre_comercial} onChange={handleChange} />
          </label>
          <label>DIRECCIÓN:
            <input name="direccion" value={form.direccion} onChange={handleChange} />
          </label>
          <button type="button" className="btn" onClick={crearCliente}>Crear Cliente</button>
        </div>

        {/* INSTALACIÓN */}
        <div className="form-column">
          <h3>INSTALACIÓN</h3>
          <label>CLIENTE:
            <select name="razon_social_instalacion" value={form.razon_social_instalacion} onChange={handleChange}>
              <option value="">-- Seleccione --</option>
              {clientes.map((cliente) => (
                <option key={cliente.id} value={cliente.id}>{cliente.razon_social}</option>
              ))}
            </select>
          </label>
          <label>CODIGO:
            <input name="codigo" value={form.codigo} onChange={handleChange} />
          </label>
          <label>NOMBRE:
            <input name="nombre_instalacion" value={form.nombre_instalacion} onChange={handleChange} />
          </label>
          <label>PROVINCIA:
            <select name="provincia" value={form.provincia} onChange={handleChange}>
              <option value="">-- Seleccione --</option>
              {provincias.map(p => <option key={p}>{p}</option>)}
            </select>
          </label>
          <label>CIUDAD:
            <select name="ciudad" value={form.ciudad} onChange={handleChange}>
              <option value="">-- Seleccione --</option>
              {ciudades.map(c => <option key={c}>{c}</option>)}
            </select>
          </label>
          <button type="button" className="btn" onClick={crearInstalacion}>Crear Instalación</button>
        </div>

        {/* PUESTO */}
        <div className="form-column">
          <h3>PUESTO</h3>
          <label>INSTALACIÓN:
            <select name="id_instalacion" value={form.id_instalacion} onChange={handleChange}>
              <option value="">-- Seleccione --</option>
              {instalaciones.map((inst) => (
                <option key={inst.id} value={inst.id}>{inst.nombre}</option>
              ))}
            </select>
          </label>
          <label>NOMBRE DEL PUESTO:
            <input name="nombre_puesto" value={form.nombre_puesto} onChange={handleChange} />
          </label>
          <button type="button" className="btn" onClick={crearPuesto}>Crear Puesto</button>
        </div>

        {/* HORARIO */}
        <div className="form-column">
          <h3>HORARIO</h3>
          <label>HORA DE INGRESO:
            <input type="time" name="hora_ingreso" value={form.hora_ingreso} onChange={handleChange} />
          </label>
          <label>HORA DE SALIDA:
            <input type="time" name="hora_salida" value={form.hora_salida} onChange={handleChange} />
          </label>
          <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <MaterialReactTable
            columns={columns}
            data={tablaHorario}
            enableColumnVisibility={false}
            enableColumnActions={false}
            enableBottomToolbar={false}
            enableColumnFilters={false}
            enableSorting={false}
            enableFullScreenToggle={false}
            enableDensityToggle={false}
            enableGlobalFilter={false}
            enablePagination={false}
            muiTableBodyCellProps={{ sx: { padding: '4px' } }}
            muiTableHeadCellProps={{ sx: { padding: '4px' } }}
            renderToolbarInternalActions={() => null}
            renderTopToolbarCustomActions={() => (
              <Box>
                <Button
                  color="primary"
                  variant="contained"
                  size="small"
                  onClick={() => setTablaHorario([...tablaHorario, { horas: '', turno: '',dias: [] }])}
                >
                  +
                </Button>
              </Box>
            )}
          />
          </div>
          <button type="button" className="btn" onClick={crearHorario}>Crear Horario</button>
        </div>
      </form>
    </div>
  );
};

export default Formulario;