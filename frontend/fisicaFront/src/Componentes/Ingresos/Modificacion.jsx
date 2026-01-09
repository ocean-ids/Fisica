// IMPORTS
import React, { useState, useEffect } from 'react';
import './Ingreso.css';
import { MaterialReactTable } from "material-react-table";
import { Box, Button } from "@mui/material";
import Swal from 'sweetalert2';
import Select from 'react-select';
import DeleteIcon from '@mui/icons-material/Delete';

/*const horas = Array.from({ length: 24 }, (_, i) => (i + 1).toString());*/
const horas = [];
for (let i = 1; i <= 24; i += 0.5) {
  horas.push(i % 1 === 0 ? i.toString() : i.toFixed(1));
}

const dias = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
const turnos = ['D', 'N'];
const tipo = ['FIJO', 'SACAFRANCO', 'SUPERVISOR'];
const Modificacion = () => {
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
  const [personas, setPersonas] = useState([]);




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


  const ModificarCliente = async () => {
    console.log("Datos del formulario:", form); 
    await fetch('http://localhost:8000/api/actualizar-cliente/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      id: form.cliente,
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
      text: 'Ocurrió un problema al modificar Cliente.',
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

  const ModificarPersona = async () => {
    console.log("Datos del formulario:", form); 
    await fetch('http://localhost:8000/api/actualizar-persona/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      id: form.persona,
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
    text: 'Ocurrió un problema al Modificar Persona.',
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
      

const fetchClientes = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/clientes/');
        const data = await res.json();
        setClientes(data);
      } catch (error) {
        console.error('Error al cargar clientes:', error);
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

    
      const fetchPersonas = async () => {
        try {
          const res = await fetch('http://localhost:8000/api/personas/');
          const data = await res.json();
          setPersonas(data);
        } catch (error) {
          console.error('Error al cargar personas:', error);
        }
      };
  useEffect(() => {
      fetchPersonas();
    }, []);



  return (
    <div className="form-wrapper">
      <form className="grid-form">

        {/* PERSONA */}
        <div className="form-column">
          <h3>MODIFICAR PERSONA</h3>
            <Select
              options={personas.map(p => ({ value: p.id, label:`${p.nombres} ${p.apellidos}` }))}
              /*onChange={selected => setForm(prev => ({ ...prev, persona: selected?.value || '' }))}*/
               onChange={selected => {
                const personaSeleccionada = personas.find(p => p.id === selected?.value);
                if (personaSeleccionada) {
                  setForm(prev => ({
                    ...prev,
                    persona: personaSeleccionada.id,
                    nombre: personaSeleccionada.nombres,
                    apellido: personaSeleccionada.apellidos,
                    cedula: personaSeleccionada.cedula,
                    tipo: personaSeleccionada.tipo,
                  }));
                } else {
                  setForm(prev => ({
                    ...prev,
                    persona: '',
                    nombre: '',
                    apellido: '',
                    cedula: '',
                    tipo: '',
                  }));
                }
              }}
              value={personas
                .map(p => ({ value: p.id, label: `${p.nombres} ${p.apellidos}` }))
                .find(opt => opt.value === form.persona)}
              placeholder="Seleccione una persona"
            />
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
           {/* <input name="tipo" value={form.tipo} onChange={handleChange} /> */}

            <select name="tipo" value={form.tipo} onChange={handleChange}>
              <option value="">-- Seleccione --</option>
              {tipo.map(p => <option key={p}>{p}</option>)}
            </select>





          </label>
          <button type="button" className="btn" onClick={ModificarPersona}>Modificar</button>
        </div>

        {/* CLIENTE */}
        <div className="form-column">
          <h3>MODIFICAR CLIENTE</h3>
            <Select
              options={clientes.map(p => ({ value: p.id, label:p.razon_social}))}
              /*onChange={selected => setForm(prev => ({ ...prev, cliente: selected?.value || '' }))}*/
              onChange={selected => {
                const clienteSeleccionado = clientes.find(p => p.id === selected?.value);
                if (clienteSeleccionado) {
                  setForm(prev => ({
                    ...prev,
                    cliente: clienteSeleccionado.id,
                    razon_social: clienteSeleccionado.razon_social,
                    nombre_comercial: clienteSeleccionado.nombre_comercial,
                    direccion: clienteSeleccionado.direccion,
                  }));
                } else {
                  setForm(prev => ({
                    ...prev,
                    cliente: '',
                    razon_social: '',
                    nombre_comercial: '',
                    direccion: ''
                  }));
                }
              }}
              value={clientes
                .map(p => ({ value: p.id, label: p.razon_social }))
                .find(opt => opt.value === form.cliente)}
              placeholder="Seleccione un cliente"
            />
          <label>RAZÓN SOCIAL:
            <input name="razon_social" value={form.razon_social} onChange={handleChange} />
          </label>
          <label>NOMBRE COMERCIAL:
            <input name="nombre_comercial" value={form.nombre_comercial} onChange={handleChange} />
          </label>
          <label>DIRECCIÓN:
            <input name="direccion" value={form.direccion} onChange={handleChange} />
          </label>
          <button type="button" className="btn" onClick={ModificarCliente}>Modificar</button>
        </div>
      </form>
    </div>
  );
};

export default Modificacion;